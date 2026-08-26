"""GeoVaris coverage raster output.

This module converts a CoverageGridPlan and CoverageCalculationResult
into a projected GeoTIFF suitable for later visualization and spatial
analysis.

Bands:
1. Predicted received power, dBm
2. Receiver-threshold margin, dB
3. Coverage mask:
   1 = meets threshold
   0 = below threshold

NoData is used for:
- cells outside the calculation radius
- transmitter-site cell
- unevaluated cells

RF outputs are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.coverage_calculation import (
    CoverageCalculationResult,
    CoverageCellStatus,
)
from geovaris_rf.coverage_grid import (
    CoverageGridPlan,
)


DEFAULT_FLOAT_NODATA = -9999.0



@dataclass(frozen=True)
class CoverageRasterResult:
    """Metadata describing a written coverage GeoTIFF."""

    raster_path: str

    crs_epsg: int

    width: int
    height: int

    resolution_m: float

    west_m: float
    south_m: float
    east_m: float
    north_m: float

    received_power_band: int = 1
    margin_band: int = 2
    coverage_mask_band: int = 3

    float_nodata: float = DEFAULT_FLOAT_NODATA


def _validate_grid(
    grid: CoverageGridPlan,
) -> None:
    if grid.width <= 0:
        raise ValueError(
            "Coverage grid width must be greater than zero."
        )

    if grid.height <= 0:
        raise ValueError(
            "Coverage grid height must be greater than zero."
        )

    if (
        not math.isfinite(grid.resolution_m)
        or grid.resolution_m <= 0.0
    ):
        raise ValueError(
            "Coverage grid resolution must be finite "
            "and greater than zero."
        )

    if len(grid.points) != grid.total_cell_count:
        raise ValueError(
            "Coverage grid point count does not match "
            "width × height."
        )


def _build_raster_arrays(
    grid: CoverageGridPlan,
    calculation: CoverageCalculationResult,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    """Build received-power, margin, and mask arrays."""

    _validate_grid(
        grid
    )

    received_power = np.full(
        (
            grid.height,
            grid.width,
        ),
        DEFAULT_FLOAT_NODATA,
        dtype=np.float32,
    )

    margin = np.full(
        (
            grid.height,
            grid.width,
        ),
        DEFAULT_FLOAT_NODATA,
        dtype=np.float32,
    )

    coverage_mask = np.full(
        (
            grid.height,
            grid.width,
        ),
        DEFAULT_FLOAT_NODATA,
        dtype=np.float32,
    )

    for cell in calculation.cells:
        if (
            cell.row < 0
            or cell.row >= grid.height
            or cell.column < 0
            or cell.column >= grid.width
        ):
            raise ValueError(
                "Coverage result contains a cell outside "
                "the coverage-grid dimensions."
            )

        if (
            cell.status
            != CoverageCellStatus.EVALUATED
        ):
            continue

        if cell.predicted_received_power_dbm is None:
            raise ValueError(
                "Evaluated coverage cell is missing "
                "predicted_received_power_dbm."
            )

        if cell.margin_db is None:
            raise ValueError(
                "Evaluated coverage cell is missing margin_db."
            )

        if cell.meets_threshold is None:
            raise ValueError(
                "Evaluated coverage cell is missing meets_threshold."
            )

        if not math.isfinite(
            cell.predicted_received_power_dbm
        ):
            raise ValueError(
                "Evaluated coverage cell has non-finite "
                "predicted received power."
            )

        if not math.isfinite(
            cell.margin_db
        ):
            raise ValueError(
                "Evaluated coverage cell has non-finite margin."
            )

        received_power[
            cell.row,
            cell.column,
        ] = float(
            cell.predicted_received_power_dbm
        )

        margin[
            cell.row,
            cell.column,
        ] = float(
            cell.margin_db
        )

        coverage_mask[
            cell.row,
            cell.column,
        ] = (
            1.0
            if cell.meets_threshold
            else 0.0
        )

    return (
        received_power,
        margin,
        coverage_mask,
    )


def write_coverage_geotiff(
    *,
    grid: CoverageGridPlan,
    calculation: CoverageCalculationResult,
    output_path: str,
) -> CoverageRasterResult:
    """Write coverage results to a three-band GeoTIFF."""

    received_power, margin, coverage_mask = (
        _build_raster_arrays(
            grid,
            calculation,
        )
    )

    path = Path(
        output_path
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    transform = from_origin(
        grid.west_m,
        grid.north_m,
        grid.resolution_m,
        grid.resolution_m,
    )

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=grid.width,
        height=grid.height,
        count=3,
        dtype="float32",
        crs=f"EPSG:{grid.crs_epsg}",
        transform=transform,
        nodata=DEFAULT_FLOAT_NODATA,
        compress="deflate",
    ) as dataset:
        dataset.write(
            received_power,
            1,
        )

        dataset.write(
            margin,
            2,
        )

        dataset.write(
            coverage_mask,
            3,
        )

        dataset.set_band_description(
            1,
            "Predicted received power (dBm)",
        )

        dataset.set_band_description(
            2,
            "Receiver threshold margin (dB)",
        )

        dataset.set_band_description(
            3,
            "Coverage mask (1=meets threshold, 0=below threshold)",
        )

        dataset.update_tags(
            product="GeoVaris Coverage Intelligence",
            output_type="coverage_raster",
            model_name=calculation.model_name,
            model_version=calculation.model_version,
            engineering_estimate="true",
        )

    return CoverageRasterResult(
        raster_path=str(
            path.resolve()
        ),
        crs_epsg=grid.crs_epsg,
        width=grid.width,
        height=grid.height,
        resolution_m=grid.resolution_m,
        west_m=grid.west_m,
        south_m=grid.south_m,
        east_m=grid.east_m,
        north_m=grid.north_m,
    )