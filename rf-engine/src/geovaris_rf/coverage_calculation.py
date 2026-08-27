"""GeoVaris RF coverage-grid calculation.

Evaluates a bounded subset of a planned coverage grid using:

- sampled terrain profiles
- a modular propagation model
- optional receiver-side land-cover / clutter classification
- optional ITU-R P.2108 terrestrial clutter correction
- RF link-budget threshold evaluation

Terrain propagation and clutter loss remain separate engineering
components so their effects and lineage remain traceable.

RF results are engineering estimates and do not guarantee service
availability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from geovaris_rf.clutter import (
    sample_clutter,
)
from geovaris_rf.clutter_loss import (
    ClutterLossRequest,
)
from geovaris_rf.clutter_policy import (
    ClutterApplicabilityStatus,
    evaluate_p2108_applicability,
)
from geovaris_rf.coverage_grid import (
    CoverageGridPlan,
    CoverageGridPoint,
)
from geovaris_rf.p2108 import (
    ONE_END_MIN_DISTANCE_M,
    P2108TerrestrialClutterModel,
)
from geovaris_rf.path_evaluation import (
    PathEvaluationRequest,
    evaluate_path,
)
from geovaris_rf.propagation import (
    PropagationModel,
    PropagationRequest,
)
from geovaris_rf.terrain_profile import (
    sample_terrain_profile,
)


class CoverageCellStatus(
    str,
    Enum,
):
    """Processing status for one coverage-grid cell."""

    EVALUATED = "evaluated"
    TRANSMITTER_SITE = "transmitter_site"


@dataclass(frozen=True)
class CoverageCellResult:
    """RF result for one coverage-grid receiver cell."""

    row: int
    column: int

    latitude: float
    longitude: float

    distance_from_site_m: float

    status: CoverageCellStatus

    # Backward-compatible underlying propagation-model loss.
    propagation_loss_db: float | None = None

    # Explicit loss components.
    terrain_loss_db: float | None = None
    clutter_loss_db: float | None = None
    total_path_loss_db: float | None = None

    predicted_received_power_dbm: float | None = None
    receiver_threshold_dbm: float | None = None
    margin_db: float | None = None
    meets_threshold: bool | None = None

    propagation_mode: str | None = None

    # Receiver-side clutter lineage.
    clutter_source_class_value: int | None = None
    clutter_class: str | None = None
    clutter_applicability_status: str | None = None
    clutter_model_name: str | None = None
    clutter_model_version: str | None = None

    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoverageCalculationResult:
    """Summary and cell results from one prototype calculation."""

    model_name: str
    model_version: str

    requested_cell_limit: int

    evaluated_cell_count: int
    transmitter_site_cell_count: int

    covered_cell_count: int
    uncovered_cell_count: int

    cells: tuple[
        CoverageCellResult,
        ...,
    ]


def _validate_positive_finite(
    value: float,
    field_name: str,
) -> None:
    """Validate a finite numeric value greater than zero."""

    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value <= 0.0
    ):
        raise ValueError(
            f"{field_name} must be a finite value "
            "greater than zero; "
            f"got {value}."
        )


def _validate_nonnegative_finite(
    value: float,
    field_name: str,
) -> None:
    """Validate a finite numeric value greater than or equal to zero."""

    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value < 0.0
    ):
        raise ValueError(
            f"{field_name} must be a finite value "
            "greater than or equal to zero; "
            f"got {value}."
        )


def _inside_radius_points(
    grid: CoverageGridPlan,
) -> tuple[
    CoverageGridPoint,
    ...,
]:
    """Return inside-radius points in deterministic grid order."""

    return tuple(
        point
        for point in grid.points
        if point.inside_radius
    )


def calculate_coverage_subset(
    *,
    model: PropagationModel,
    grid: CoverageGridPlan,
    dem_raster_path: str,
    frequency_mhz: float,
    transmitter_height_agl_m: float,
    receiver_height_agl_m: float,
    terrain_sample_spacing_m: float,
    eirp_dbm: float,
    receiver_gain_dbi: float,
    additional_losses_db: float,
    receiver_threshold_dbm: float,
    max_propagation_cells: int,
    clutter_raster_path: str | None = None,
    clutter_percentage_locations: float = 50.0,
) -> CoverageCalculationResult:
    """Evaluate a bounded deterministic subset of a coverage grid.

    Cells are processed in the same row-major order stored by the
    CoverageGridPlan.

    The transmitter-site cell is explicitly identified and is not
    passed to the propagation model because its path distance is zero.

    ``max_propagation_cells`` limits only actual propagation
    calculations.

    When ``clutter_raster_path`` is supplied, the receiver location is
    sampled from the clutter raster.

    GeoVaris then:

    1. maps the source land-cover class into a normalized clutter class;
    2. evaluates P.2108 applicability;
    3. applies receiver-side P.2108 loss only when applicable and the
       path satisfies the model's minimum-distance requirement;
    4. preserves explicit clutter lineage even when no clutter loss is
       calculated.

    No clutter raster means the pre-clutter behavior is preserved.
    """

    if max_propagation_cells <= 0:
        raise ValueError(
            "max_propagation_cells must be greater than zero; "
            f"got {max_propagation_cells}."
        )

    _validate_positive_finite(
        terrain_sample_spacing_m,
        "terrain_sample_spacing_m",
    )

    _validate_nonnegative_finite(
        transmitter_height_agl_m,
        "transmitter_height_agl_m",
    )

    _validate_nonnegative_finite(
        receiver_height_agl_m,
        "receiver_height_agl_m",
    )

    if not math.isfinite(
        frequency_mhz
    ):
        raise ValueError(
            "frequency_mhz must be finite."
        )

    if not math.isfinite(
        eirp_dbm
    ):
        raise ValueError(
            "eirp_dbm must be finite."
        )

    if not math.isfinite(
        receiver_gain_dbi
    ):
        raise ValueError(
            "receiver_gain_dbi must be finite."
        )

    _validate_nonnegative_finite(
        additional_losses_db,
        "additional_losses_db",
    )

    if not math.isfinite(
        receiver_threshold_dbm
    ):
        raise ValueError(
            "receiver_threshold_dbm must be finite."
        )

    results: list[
        CoverageCellResult
    ] = []

    evaluated_cell_count = 0
    transmitter_site_cell_count = 0
    covered_cell_count = 0
    uncovered_cell_count = 0

    for point in _inside_radius_points(
        grid
    ):
        if math.isclose(
            point.distance_from_site_m,
            0.0,
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            transmitter_site_cell_count += 1

            results.append(
                CoverageCellResult(
                    row=point.row,
                    column=point.column,
                    latitude=point.latitude,
                    longitude=point.longitude,
                    distance_from_site_m=(
                        point.distance_from_site_m
                    ),
                    status=(
                        CoverageCellStatus
                        .TRANSMITTER_SITE
                    ),
                )
            )

            continue

        if (
            evaluated_cell_count
            >= max_propagation_cells
        ):
            break

        terrain_profile = (
            sample_terrain_profile(
                dem_raster_path,
                grid.site_latitude,
                grid.site_longitude,
                point.latitude,
                point.longitude,
                terrain_sample_spacing_m,
            )
        )

        propagation_request = (
            PropagationRequest(
                frequency_mhz=frequency_mhz,
                transmitter_height_agl_m=(
                    transmitter_height_agl_m
                ),
                receiver_height_agl_m=(
                    receiver_height_agl_m
                ),
                terrain_profile=terrain_profile,
            )
        )

        clutter_sample = None
        clutter_applicability = None
        clutter_loss_result = None

        clutter_warnings: list[
            str
        ] = []

        if clutter_raster_path is not None:
            clutter_sample = (
                sample_clutter(
                    raster_path=(
                        clutter_raster_path
                    ),
                    latitude=point.latitude,
                    longitude=point.longitude,
                )
            )

            clutter_applicability = (
                evaluate_p2108_applicability(
                    clutter_sample
                    .clutter_class
                )
            )

            if (
                clutter_applicability.status
                == (
                    ClutterApplicabilityStatus
                    .APPLICABLE
                )
            ):
                if (
                    point.distance_from_site_m
                    >= ONE_END_MIN_DISTANCE_M
                ):
                    clutter_model = (
                        P2108TerrestrialClutterModel()
                    )

                    clutter_loss_result = (
                        clutter_model.calculate(
                            ClutterLossRequest(
                                frequency_mhz=(
                                    frequency_mhz
                                ),
                                clutter_class=(
                                    clutter_sample
                                    .clutter_class
                                ),
                                path_distance_m=(
                                    point
                                    .distance_from_site_m
                                ),
                                transmitter_height_agl_m=(
                                    transmitter_height_agl_m
                                ),
                                receiver_height_agl_m=(
                                    receiver_height_agl_m
                                ),
                                model_parameters={
                                    "percentage_locations": (
                                        clutter_percentage_locations
                                    ),
                                    "correction_end": (
                                        "receiver"
                                    ),
                                },
                            )
                        )
                    )

                    clutter_warnings.extend(
                        clutter_loss_result
                        .warnings
                    )

                else:
                    clutter_warnings.append(
                        "P.2108-1 §3.2 receiver-side "
                        "clutter correction was not "
                        "evaluated because path distance "
                        f"{point.distance_from_site_m:.2f} m "
                        "is below the 250 m minimum."
                    )

            elif (
                clutter_applicability.status
                == (
                    ClutterApplicabilityStatus
                    .FUTURE_MODEL
                )
            ):
                clutter_warnings.append(
                    clutter_applicability
                    .reason
                )

        path_result = evaluate_path(
            model,
            PathEvaluationRequest(
                propagation_request=(
                    propagation_request
                ),
                eirp_dbm=eirp_dbm,
                clutter_loss=(
                    clutter_loss_result
                ),
                receiver_gain_dbi=(
                    receiver_gain_dbi
                ),
                additional_losses_db=(
                    additional_losses_db
                ),
                receiver_threshold_dbm=(
                    receiver_threshold_dbm
                ),
            ),
        )

        evaluated_cell_count += 1

        if path_result.meets_threshold:
            covered_cell_count += 1
        else:
            uncovered_cell_count += 1

        results.append(
            CoverageCellResult(
                row=point.row,
                column=point.column,
                latitude=point.latitude,
                longitude=point.longitude,
                distance_from_site_m=(
                    point.distance_from_site_m
                ),
                status=(
                    CoverageCellStatus
                    .EVALUATED
                ),
                propagation_loss_db=(
                    path_result
                    .propagation_loss_db
                ),
                terrain_loss_db=(
                    path_result
                    .terrain_loss_db
                ),
                clutter_loss_db=(
                    path_result
                    .clutter_loss_db
                ),
                total_path_loss_db=(
                    path_result
                    .total_path_loss_db
                ),
                predicted_received_power_dbm=(
                    path_result
                    .predicted_received_power_dbm
                ),
                receiver_threshold_dbm=(
                    path_result
                    .receiver_threshold_dbm
                ),
                margin_db=(
                    path_result
                    .margin_db
                ),
                meets_threshold=(
                    path_result
                    .meets_threshold
                ),
                propagation_mode=(
                    path_result
                    .propagation
                    .propagation_mode
                ),
                clutter_source_class_value=(
                    None
                    if clutter_sample is None
                    else (
                        clutter_sample
                        .source_class_value
                    )
                ),
                clutter_class=(
                    None
                    if clutter_sample is None
                    else (
                        clutter_sample
                        .clutter_class
                        .value
                    )
                ),
                clutter_applicability_status=(
                    None
                    if clutter_applicability is None
                    else (
                        clutter_applicability
                        .status
                        .value
                    )
                ),
                clutter_model_name=(
                    None
                    if clutter_loss_result is None
                    else (
                        clutter_loss_result
                        .model_name
                    )
                ),
                clutter_model_version=(
                    None
                    if clutter_loss_result is None
                    else (
                        clutter_loss_result
                        .model_version
                    )
                ),
                warnings=(
                    path_result
                    .propagation
                    .warnings
                    + tuple(
                        clutter_warnings
                    )
                ),
            )
        )

    return CoverageCalculationResult(
        model_name=model.model_name,
        model_version=model.model_version,
        requested_cell_limit=(
            max_propagation_cells
        ),
        evaluated_cell_count=(
            evaluated_cell_count
        ),
        transmitter_site_cell_count=(
            transmitter_site_cell_count
        ),
        covered_cell_count=(
            covered_cell_count
        ),
        uncovered_cell_count=(
            uncovered_cell_count
        ),
        cells=tuple(
            results
        ),
    )