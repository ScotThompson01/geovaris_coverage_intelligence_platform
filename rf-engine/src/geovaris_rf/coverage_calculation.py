"""GeoVaris coverage calculation prototype.

This module evaluates a bounded subset of coverage-grid receiver cells.

Current MVP responsibilities:
- Select deterministic grid cells inside the requested radius.
- Skip the transmitter-site cell for propagation calculation.
- Sample a terrain profile from the transmitter to each receiver cell.
- Run the selected propagation model.
- Evaluate the RF link budget and receiver threshold.
- Preserve per-cell RF results and summary counts.

This module intentionally does not yet write a raster or polygon.

RF predictions are engineering estimates and do not guarantee
actual service availability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from geovaris_rf.coverage_grid import (
    CoverageGridPlan,
    CoverageGridPoint,
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


class CoverageCellStatus(str, Enum):
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

    propagation_loss_db: float | None = None
    predicted_received_power_dbm: float | None = None
    receiver_threshold_dbm: float | None = None
    margin_db: float | None = None
    meets_threshold: bool | None = None

    propagation_mode: str | None = None

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

    cells: tuple[CoverageCellResult, ...]


def _validate_positive_finite(
    value: float,
    field_name: str,
) -> None:
    if (
        not math.isfinite(value)
        or value <= 0.0
    ):
        raise ValueError(
            f"{field_name} must be finite and greater "
            f"than zero; got {value}."
        )


def _validate_nonnegative_finite(
    value: float,
    field_name: str,
) -> None:
    if (
        not math.isfinite(value)
        or value < 0.0
    ):
        raise ValueError(
            f"{field_name} must be finite and zero "
            f"or greater; got {value}."
        )


def _inside_radius_points(
    grid: CoverageGridPlan,
) -> tuple[CoverageGridPoint, ...]:
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
) -> CoverageCalculationResult:
    """Evaluate a bounded deterministic subset of a coverage grid.

    Cells are processed in the same row-major order stored by the
    CoverageGridPlan.

    The transmitter-site cell is explicitly identified and is not
    passed to the propagation model because its path distance is zero.

    max_propagation_cells limits only actual propagation calculations.
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

    results: list[CoverageCellResult] = []

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

        terrain_profile = sample_terrain_profile(
            dem_raster_path,
            grid.site_latitude,
            grid.site_longitude,
            point.latitude,
            point.longitude,
            terrain_sample_spacing_m,
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

        path_result = evaluate_path(
            model,
            PathEvaluationRequest(
                propagation_request=(
                    propagation_request
                ),
                eirp_dbm=eirp_dbm,
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
                    CoverageCellStatus.EVALUATED
                ),
                propagation_loss_db=(
                    path_result
                    .propagation_loss_db
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
                    path_result.margin_db
                ),
                meets_threshold=(
                    path_result.meets_threshold
                ),
                propagation_mode=(
                    path_result
                    .propagation
                    .propagation_mode
                ),
                warnings=(
                    path_result
                    .propagation
                    .warnings
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