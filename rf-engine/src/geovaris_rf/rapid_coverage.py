"""Rapid Coverage Estimate raster processing for GeoVaris.

This module combines:

1. Terrain/clutter line-of-sight visibility.
2. Free-space link-budget maximum range.

The resulting binary raster represents the GeoVaris:

    Rapid Coverage Estimate
    Terrain/Clutter LOS + Free-Space Link Budget

A cell is estimated covered only when:

    viewshed_visible
    AND
    distance_from_transmitter <= FSPL maximum range

This module does not calculate per-cell received signal level.

It is not Longley-Rice / ITM propagation.

RF results are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

from geovaris_rf.dem import (
    validate_coordinate,
)
from geovaris_rf.free_space import (
    FreeSpaceRangeResult,
    calculate_free_space_range,
)
from geovaris_rf.viewshed import (
    VIEWSHED_NODATA_VALUE,
    VIEWSHED_NOT_VISIBLE_VALUE,
    VIEWSHED_VISIBLE_VALUE,
)


RAPID_COVERAGE_NOT_COVERED_VALUE = 0
RAPID_COVERAGE_COVERED_VALUE = 1
RAPID_COVERAGE_NODATA_VALUE = 255

RAPID_COVERAGE_METHOD_NAME = (
    "Rapid Coverage Estimate"
)

RAPID_COVERAGE_METHOD_DESCRIPTION = (
    "Terrain/Clutter LOS + Free-Space Link Budget"
)

GRID_ALIGNMENT_TOLERANCE = 1e-6


@dataclass(frozen=True)
class RapidCoverageResult:
    """Metadata describing one Rapid Coverage Estimate raster."""

    viewshed_path: str
    destination_path: str

    method_name: str
    method_description: str

    target_crs: str

    width_px: int
    height_px: int

    resolution_x_m: float
    resolution_y_m: float

    observer_latitude: float
    observer_longitude: float
    observer_x_m: float
    observer_y_m: float

    frequency_mhz: float
    eirp_dbm: float
    receiver_gain_dbi: float
    additional_losses_db: float
    receiver_threshold_dbm: float

    maximum_path_loss_db: float
    fspl_maximum_distance_m: float

    calculation_radius_m: float
    effective_maximum_distance_m: float

    covered_cell_count: int
    evaluated_cell_count: int

    covered_value: int
    not_covered_value: int
    nodata_value: int


def _validate_finite(
    value: float,
    *,
    name: str,
) -> float:
    """Validate one finite numeric input."""

    numeric_value = float(
        value
    )

    if not math.isfinite(
        numeric_value
    ):
        raise ValueError(
            f"{name} must be finite."
        )

    return numeric_value


def _validate_positive(
    value: float,
    *,
    name: str,
) -> float:
    """Validate one finite positive numeric input."""

    numeric_value = _validate_finite(
        value,
        name=name,
    )

    if numeric_value <= 0:
        raise ValueError(
            f"{name} must be greater than zero."
        )

    return numeric_value


def _validate_viewshed_dataset(
    dataset: rasterio.io.DatasetReader,
) -> None:
    """Validate a viewshed raster for Rapid processing."""

    if dataset.count != 1:
        raise ValueError(
            "Viewshed raster must contain exactly one band."
        )

    if dataset.crs is None:
        raise ValueError(
            "Viewshed raster does not define a CRS."
        )

    if not dataset.crs.is_projected:
        raise ValueError(
            "Viewshed raster must use a projected CRS."
        )

    if dataset.width <= 0 or dataset.height <= 0:
        raise ValueError(
            "Viewshed raster dimensions must be greater than zero."
        )

    if (
        abs(
            float(
                dataset.transform.b
            )
        )
        > GRID_ALIGNMENT_TOLERANCE
        or abs(
            float(
                dataset.transform.d
            )
        )
        > GRID_ALIGNMENT_TOLERANCE
    ):
        raise ValueError(
            "Rotated viewshed rasters are not currently supported."
        )


def build_rapid_coverage_mask(
    *,
    viewshed_values: np.ma.MaskedArray,
    transform: rasterio.Affine,
    observer_x_m: float,
    observer_y_m: float,
    maximum_distance_m: float,
) -> np.ndarray:
    """Intersect binary LOS visibility with maximum RF range.

    Input viewshed convention:

        1   visible
        0   not visible
        255 NoData

    Output convention:

        1   estimated covered
        0   not estimated covered
        255 NoData
    """

    maximum_distance_m = (
        _validate_positive(
            maximum_distance_m,
            name="maximum_distance_m",
        )
    )

    if viewshed_values.ndim != 2:
        raise ValueError(
            "Viewshed array must be two-dimensional."
        )

    observer_x_m = _validate_finite(
        observer_x_m,
        name="observer_x_m",
    )

    observer_y_m = _validate_finite(
        observer_y_m,
        name="observer_y_m",
    )

    if (
        abs(
            float(
                transform.b
            )
        )
        > GRID_ALIGNMENT_TOLERANCE
        or abs(
            float(
                transform.d
            )
        )
        > GRID_ALIGNMENT_TOLERANCE
    ):
        raise ValueError(
            "Rotated raster transforms are not currently supported."
        )

    source_mask = np.ma.getmaskarray(
        viewshed_values
    )

    source_data = np.asarray(
        viewshed_values.filled(
            VIEWSHED_NODATA_VALUE
        ),
        dtype=np.uint8,
    )

    valid_values = source_data[
        ~source_mask
    ]

    if valid_values.size:
        supported_values = np.isin(
            valid_values,
            [
                VIEWSHED_NOT_VISIBLE_VALUE,
                VIEWSHED_VISIBLE_VALUE,
            ],
        )

        if not bool(
            np.all(
                supported_values
            )
        ):
            raise ValueError(
                "Viewshed raster contains unsupported values."
            )

    rows = np.arange(
        viewshed_values.shape[0],
        dtype=np.float64,
    )

    columns = np.arange(
        viewshed_values.shape[1],
        dtype=np.float64,
    )

    x_centers = (
        float(
            transform.c
        )
        + (
            columns
            + 0.5
        )
        * float(
            transform.a
        )
    )

    y_centers = (
        float(
            transform.f
        )
        + (
            rows
            + 0.5
        )
        * float(
            transform.e
        )
    )

    distance_squared = (
        (
            x_centers[
                np.newaxis,
                :
            ]
            - observer_x_m
        )
        ** 2
        + (
            y_centers[
                :,
                np.newaxis
            ]
            - observer_y_m
        )
        ** 2
    )

    inside_range = (
        distance_squared
        <= maximum_distance_m
        ** 2
    )

    covered = (
        ~source_mask
        & inside_range
        & (
            source_data
            == VIEWSHED_VISIBLE_VALUE
        )
    )

    result = np.full(
        viewshed_values.shape,
        RAPID_COVERAGE_NOT_COVERED_VALUE,
        dtype=np.uint8,
    )

    result[
        covered
    ] = (
        RAPID_COVERAGE_COVERED_VALUE
    )

    result[
        source_mask
    ] = (
        RAPID_COVERAGE_NODATA_VALUE
    )

    return result


def build_rapid_coverage_raster(
    *,
    viewshed_path: str | Path,
    destination_path: str | Path,
    observer_latitude: float,
    observer_longitude: float,
    frequency_mhz: float,
    eirp_dbm: float,
    receiver_threshold_dbm: float,
    calculation_radius_m: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> RapidCoverageResult:
    """Create one GeoVaris Rapid Coverage Estimate raster."""

    validate_coordinate(
        observer_latitude,
        observer_longitude,
    )

    calculation_radius_m = (
        _validate_positive(
            calculation_radius_m,
            name="calculation_radius_m",
        )
    )

    free_space_result: FreeSpaceRangeResult = (
        calculate_free_space_range(
            frequency_mhz=frequency_mhz,
            eirp_dbm=eirp_dbm,
            receiver_threshold_dbm=(
                receiver_threshold_dbm
            ),
            receiver_gain_dbi=(
                receiver_gain_dbi
            ),
            additional_losses_db=(
                additional_losses_db
            ),
        )
    )

    effective_maximum_distance_m = min(
        calculation_radius_m,
        free_space_result.maximum_distance_m,
    )

    viewshed_path = Path(
        viewshed_path
    ).expanduser().resolve()

    destination_path = Path(
        destination_path
    ).expanduser().resolve()

    if not viewshed_path.is_file():
        raise FileNotFoundError(
            f"Viewshed raster does not exist: {viewshed_path}"
        )

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination_path.exists():
        destination_path.unlink()

    try:
        with rasterio.open(
            viewshed_path
        ) as viewshed:
            _validate_viewshed_dataset(
                viewshed
            )

            transformer = Transformer.from_crs(
                "EPSG:4326",
                viewshed.crs,
                always_xy=True,
            )

            (
                observer_x_m,
                observer_y_m,
            ) = transformer.transform(
                observer_longitude,
                observer_latitude,
            )

            observer_row, observer_col = (
                viewshed.index(
                    observer_x_m,
                    observer_y_m,
                )
            )

            if (
                observer_row < 0
                or observer_row >= viewshed.height
                or observer_col < 0
                or observer_col >= viewshed.width
            ):
                raise ValueError(
                    "Observer location is outside the viewshed grid."
                )

            viewshed_values = viewshed.read(
                1,
                masked=True,
            )

            if np.ma.getmaskarray(
                viewshed_values
            )[
                observer_row,
                observer_col,
            ]:
                raise ValueError(
                    "Observer location falls on a NoData cell."
                )

            rapid_mask = (
                build_rapid_coverage_mask(
                    viewshed_values=(
                        viewshed_values
                    ),
                    transform=(
                        viewshed.transform
                    ),
                    observer_x_m=(
                        observer_x_m
                    ),
                    observer_y_m=(
                        observer_y_m
                    ),
                    maximum_distance_m=(
                        effective_maximum_distance_m
                    ),
                )
            )

            profile = viewshed.profile.copy()

            profile.update(
                driver="GTiff",
                dtype="uint8",
                count=1,
                nodata=(
                    RAPID_COVERAGE_NODATA_VALUE
                ),
                compress="deflate",
            )

            target_crs = str(
                viewshed.crs
            )

            width_px = viewshed.width
            height_px = viewshed.height

            resolution_x_m = abs(
                float(
                    viewshed.res[0]
                )
            )

            resolution_y_m = abs(
                float(
                    viewshed.res[1]
                )
            )

            with rasterio.open(
                destination_path,
                "w",
                **profile,
            ) as destination:
                destination.write(
                    rapid_mask,
                    1,
                )

                destination.set_band_description(
                    1,
                    (
                        "Rapid Coverage Estimate "
                        "(1=covered, 0=not covered)"
                    ),
                )

                destination.update_tags(
                    product=(
                        "GeoVaris Coverage Intelligence"
                    ),
                    output_type=(
                        "rapid_coverage_raster"
                    ),
                    analysis_method=(
                        RAPID_COVERAGE_METHOD_NAME
                    ),
                    methodology=(
                        RAPID_COVERAGE_METHOD_DESCRIPTION
                    ),
                    engineering_estimate="true",
                    frequency_mhz=str(
                        free_space_result.frequency_mhz
                    ),
                    eirp_dbm=str(
                        free_space_result.eirp_dbm
                    ),
                    receiver_gain_dbi=str(
                        free_space_result.receiver_gain_dbi
                    ),
                    additional_losses_db=str(
                        free_space_result.additional_losses_db
                    ),
                    receiver_threshold_dbm=str(
                        free_space_result.receiver_threshold_dbm
                    ),
                    maximum_path_loss_db=str(
                        free_space_result.maximum_path_loss_db
                    ),
                    fspl_maximum_distance_m=str(
                        free_space_result.maximum_distance_m
                    ),
                    calculation_radius_m=str(
                        calculation_radius_m
                    ),
                    effective_maximum_distance_m=str(
                        effective_maximum_distance_m
                    ),
                    source_viewshed_path=str(
                        viewshed_path
                    ),
                )

        covered_cell_count = int(
            np.count_nonzero(
                rapid_mask
                == RAPID_COVERAGE_COVERED_VALUE
            )
        )

        evaluated_cell_count = int(
            np.count_nonzero(
                rapid_mask
                != RAPID_COVERAGE_NODATA_VALUE
            )
        )

    except Exception:
        if destination_path.exists():
            destination_path.unlink()

        raise

    return RapidCoverageResult(
        viewshed_path=str(
            viewshed_path
        ),
        destination_path=str(
            destination_path
        ),
        method_name=(
            RAPID_COVERAGE_METHOD_NAME
        ),
        method_description=(
            RAPID_COVERAGE_METHOD_DESCRIPTION
        ),
        target_crs=target_crs,
        width_px=width_px,
        height_px=height_px,
        resolution_x_m=resolution_x_m,
        resolution_y_m=resolution_y_m,
        observer_latitude=float(
            observer_latitude
        ),
        observer_longitude=float(
            observer_longitude
        ),
        observer_x_m=float(
            observer_x_m
        ),
        observer_y_m=float(
            observer_y_m
        ),
        frequency_mhz=(
            free_space_result.frequency_mhz
        ),
        eirp_dbm=(
            free_space_result.eirp_dbm
        ),
        receiver_gain_dbi=(
            free_space_result.receiver_gain_dbi
        ),
        additional_losses_db=(
            free_space_result.additional_losses_db
        ),
        receiver_threshold_dbm=(
            free_space_result.receiver_threshold_dbm
        ),
        maximum_path_loss_db=(
            free_space_result.maximum_path_loss_db
        ),
        fspl_maximum_distance_m=(
            free_space_result.maximum_distance_m
        ),
        calculation_radius_m=(
            calculation_radius_m
        ),
        effective_maximum_distance_m=(
            effective_maximum_distance_m
        ),
        covered_cell_count=(
            covered_cell_count
        ),
        evaluated_cell_count=(
            evaluated_cell_count
        ),
        covered_value=(
            RAPID_COVERAGE_COVERED_VALUE
        ),
        not_covered_value=(
            RAPID_COVERAGE_NOT_COVERED_VALUE
        ),
        nodata_value=(
            RAPID_COVERAGE_NODATA_VALUE
        ),
    )