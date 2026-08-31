"""Fast terrain/clutter viewshed processing for GeoVaris.

This module wraps GDAL's validated viewshed implementation for the
GeoVaris Rapid Coverage Estimate methodology.

The input obstruction surface is:

    effective elevation =
        bare-earth DEM elevation
        + governed clutter height

Important endpoint handling:

GDAL interprets observer and target heights relative to the input
elevation surface. Because the GeoVaris effective surface already
contains clutter height, antenna heights cannot simply be added to that
surface.

For the transmitter:

    GDAL observer height =
        transmitter height AGL
        - local transmitter clutter height

For each receiver cell:

    available receiver height above effective surface =
        receiver height AGL
        - local clutter height

GeoVaris therefore runs GDAL viewshed in GROUND mode to obtain the
minimum target height above the effective surface required for
visibility, then compares that value against the actual receiver height
relative to the effective surface.

Earth curvature and atmospheric refraction are represented using the
same effective-Earth-radius k-factor convention already used elsewhere
in GeoVaris.

For GDAL:

    curvature coefficient = 1 / k_factor

Thus the GeoVaris default:

    k_factor = 4 / 3

corresponds to:

    GDAL curvature coefficient = 0.75

This is line-of-sight geometry, not an RF propagation model.

RF results are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

from geovaris_rf.dem import (
    validate_coordinate,
)
from geovaris_rf.dem_raster import (
    DEFAULT_DEM_NODATA,
)
from geovaris_rf.terrain_analysis import (
    DEFAULT_K_FACTOR,
)


GDAL_VIEWSHED_PATH_ENV = (
    "GEOVARIS_GDAL_VIEWSHED_PATH"
)

VIEWSHED_VISIBLE_VALUE = 1
VIEWSHED_NOT_VISIBLE_VALUE = 0
VIEWSHED_NODATA_VALUE = 255

GRID_ALIGNMENT_TOLERANCE = 1e-6
CLUTTER_HEIGHT_TOLERANCE_M = 1e-4


@dataclass(frozen=True)
class ViewshedResult:
    """Metadata describing one GeoVaris viewshed calculation."""

    dem_path: str
    effective_surface_path: str
    destination_path: str

    gdal_viewshed_path: str
    gdal_version: str

    target_crs: str
    width_px: int
    height_px: int
    resolution_x_m: float
    resolution_y_m: float

    observer_latitude: float
    observer_longitude: float
    observer_x_m: float
    observer_y_m: float

    transmitter_height_agl_m: float
    receiver_height_agl_m: float
    observer_clutter_height_m: float
    gdal_observer_height_m: float

    calculation_radius_m: float

    k_factor: float
    curvature_coefficient: float

    visible_value: int
    not_visible_value: int
    nodata_value: int

    visible_cell_count: int
    evaluated_cell_count: int


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


def _validate_nonnegative(
    value: float,
    *,
    name: str,
) -> float:
    """Validate one finite nonnegative numeric input."""

    numeric_value = _validate_finite(
        value,
        name=name,
    )

    if numeric_value < 0:
        raise ValueError(
            f"{name} must be zero or greater."
        )

    return numeric_value


def k_factor_to_curvature_coefficient(
    k_factor: float,
) -> float:
    """Convert effective-Earth k-factor to GDAL curvature coefficient."""

    k_factor = _validate_finite(
        k_factor,
        name="k_factor",
    )

    if k_factor <= 0:
        raise ValueError(
            "k_factor must be greater than zero."
        )

    return (
        1.0
        / k_factor
    )


def resolve_gdal_viewshed_path(
    explicit_path: str | Path | None = None,
) -> Path:
    """Resolve the GDAL viewshed executable.

    Resolution order:
    1. Explicit function argument.
    2. GEOVARIS_GDAL_VIEWSHED_PATH environment variable.
    3. Current process PATH.

    GeoVaris does not silently hard-code a specific QGIS/GDAL install
    location because production and development environments may use
    different GDAL distributions.
    """

    candidate: str | Path | None = (
        explicit_path
    )

    if candidate is None:
        environment_value = os.getenv(
            GDAL_VIEWSHED_PATH_ENV
        )

        if environment_value:
            candidate = (
                environment_value
            )

    if candidate is None:
        discovered = shutil.which(
            "gdal_viewshed"
        )

        if discovered:
            candidate = discovered

    if candidate is None:
        raise FileNotFoundError(
            "GDAL viewshed executable was not found. "
            f"Set {GDAL_VIEWSHED_PATH_ENV} to the full "
            "path of gdal_viewshed.exe."
        )

    path = Path(
        candidate
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            "GDAL viewshed executable does not exist: "
            f"{path}"
        )

    if not path.is_file():
        raise ValueError(
            "GDAL viewshed path is not a file: "
            f"{path}"
        )

    return path


def get_gdal_version(
    gdal_viewshed_path: str | Path,
) -> str:
    """Return GDAL version text for calculation lineage."""

    path = resolve_gdal_viewshed_path(
        gdal_viewshed_path
    )

    completed = subprocess.run(
        [
            str(path),
            "--version",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    version = (
        completed.stdout.strip()
        or completed.stderr.strip()
    )

    if not version:
        raise RuntimeError(
            "GDAL did not return version information."
        )

    return version


def _transforms_match(
    first: rasterio.Affine,
    second: rasterio.Affine,
) -> bool:
    """Return whether two raster transforms match."""

    return all(
        math.isclose(
            float(actual),
            float(expected),
            rel_tol=0.0,
            abs_tol=(
                GRID_ALIGNMENT_TOLERANCE
            ),
        )
        for actual, expected in zip(
            first,
            second,
        )
    )


def _validate_aligned_datasets(
    dem: rasterio.io.DatasetReader,
    effective_surface: rasterio.io.DatasetReader,
) -> None:
    """Validate exact DEM/effective-surface grid alignment."""

    if dem.count != 1:
        raise ValueError(
            "DEM raster must contain exactly one band."
        )

    if effective_surface.count != 1:
        raise ValueError(
            "Effective surface raster must contain "
            "exactly one band."
        )

    if dem.crs is None:
        raise ValueError(
            "DEM raster does not define a CRS."
        )

    if effective_surface.crs is None:
        raise ValueError(
            "Effective surface raster does not define a CRS."
        )

    if not dem.crs.is_projected:
        raise ValueError(
            "Viewshed DEM must use a projected CRS."
        )

    if dem.crs != effective_surface.crs:
        raise ValueError(
            "DEM and effective surface CRS do not match."
        )

    if (
        dem.width
        != effective_surface.width
        or dem.height
        != effective_surface.height
    ):
        raise ValueError(
            "DEM and effective surface dimensions do not match."
        )

    if not _transforms_match(
        dem.transform,
        effective_surface.transform,
    ):
        raise ValueError(
            "DEM and effective surface transforms do not match."
        )


def build_binary_viewshed_mask(
    *,
    dem_values: np.ma.MaskedArray,
    effective_surface_values: np.ma.MaskedArray,
    minimum_target_height_values: np.ma.MaskedArray,
    transform: rasterio.Affine,
    observer_x_m: float,
    observer_y_m: float,
    receiver_height_agl_m: float,
    calculation_radius_m: float,
) -> np.ndarray:
    """Build binary LOS mask from GDAL GROUND-mode output.

    ``minimum_target_height_values`` contains the minimum target height
    above the effective obstruction surface required for visibility.

    The actual receiver height relative to that same surface is:

        receiver_height_agl_m - clutter_height_m

    Cells outside the requested calculation radius are marked not
    visible.

    Cells with unavailable DEM/effective/GDAL data are marked NoData.
    """

    receiver_height_agl_m = (
        _validate_nonnegative(
            receiver_height_agl_m,
            name="receiver_height_agl_m",
        )
    )

    calculation_radius_m = (
        _validate_finite(
            calculation_radius_m,
            name="calculation_radius_m",
        )
    )

    if calculation_radius_m <= 0:
        raise ValueError(
            "calculation_radius_m must be greater than zero."
        )

    if (
        dem_values.shape
        != effective_surface_values.shape
        or dem_values.shape
        != minimum_target_height_values.shape
    ):
        raise ValueError(
            "Viewshed input arrays must have matching shapes."
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

    dem_data = np.asarray(
        dem_values.filled(
            DEFAULT_DEM_NODATA
        ),
        dtype=np.float32,
    )

    effective_data = np.asarray(
        effective_surface_values.filled(
            DEFAULT_DEM_NODATA
        ),
        dtype=np.float32,
    )

    minimum_target_data = np.asarray(
        minimum_target_height_values.filled(
            DEFAULT_DEM_NODATA
        ),
        dtype=np.float64,
    )

    combined_mask = (
        np.ma.getmaskarray(
            dem_values
        )
        | np.ma.getmaskarray(
            effective_surface_values
        )
        | np.ma.getmaskarray(
            minimum_target_height_values
        )
    )

    clutter_height_m = (
        effective_data
        - dem_data
    )

    valid_clutter = clutter_height_m[
        ~combined_mask
    ]

    if valid_clutter.size:
        minimum_clutter = float(
            valid_clutter.min()
        )

        if (
            minimum_clutter
            < -CLUTTER_HEIGHT_TOLERANCE_M
        ):
            raise ValueError(
                "Effective surface is below the DEM in "
                "one or more valid cells."
            )

    clutter_height_m = np.maximum(
        clutter_height_m,
        0.0,
    )

    available_receiver_height_m = np.full(
        dem_values.shape,
        receiver_height_agl_m,
        dtype=np.float32,
    )
    
    rows = np.arange(
        dem_values.shape[0],
        dtype=np.float64,
    )

    columns = np.arange(
        dem_values.shape[1],
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

    inside_radius = (
        distance_squared
        <= calculation_radius_m
        ** 2
    )

    visible = (
        ~combined_mask
        & inside_radius
        & (
            available_receiver_height_m
            >= minimum_target_data
        )
    )

    result = np.full(
        dem_values.shape,
        VIEWSHED_NOT_VISIBLE_VALUE,
        dtype=np.uint8,
    )

    result[
        visible
    ] = (
        VIEWSHED_VISIBLE_VALUE
    )

    result[
        combined_mask
    ] = (
        VIEWSHED_NODATA_VALUE
    )

    return result


def build_viewshed_raster(
    *,
    dem_path: str | Path,
    effective_surface_path: str | Path,
    destination_path: str | Path,
    observer_latitude: float,
    observer_longitude: float,
    transmitter_height_agl_m: float,
    receiver_height_agl_m: float,
    calculation_radius_m: float,
    k_factor: float = DEFAULT_K_FACTOR,
    gdal_viewshed_path: str | Path | None = None,
) -> ViewshedResult:
    """Create a curvature-adjusted binary terrain/clutter viewshed.

    The resulting raster contains:

        1   visible
        0   not visible or outside calculation radius
        255 NoData / unavailable source data

    This function does not calculate RF path loss.

    The free-space link-budget range is applied separately by the Rapid
    Coverage Estimate workflow.
    """

    validate_coordinate(
        observer_latitude,
        observer_longitude,
    )

    transmitter_height_agl_m = (
        _validate_nonnegative(
            transmitter_height_agl_m,
            name="transmitter_height_agl_m",
        )
    )

    receiver_height_agl_m = (
        _validate_nonnegative(
            receiver_height_agl_m,
            name="receiver_height_agl_m",
        )
    )

    calculation_radius_m = (
        _validate_finite(
            calculation_radius_m,
            name="calculation_radius_m",
        )
    )

    if calculation_radius_m <= 0:
        raise ValueError(
            "calculation_radius_m must be greater than zero."
        )

    curvature_coefficient = (
        k_factor_to_curvature_coefficient(
            k_factor
        )
    )

    executable = (
        resolve_gdal_viewshed_path(
            gdal_viewshed_path
        )
    )

    gdal_version = get_gdal_version(
        executable
    )

    dem_path = Path(
        dem_path
    ).expanduser().resolve()

    effective_surface_path = Path(
        effective_surface_path
    ).expanduser().resolve()

    destination_path = Path(
        destination_path
    ).expanduser().resolve()

    if not dem_path.is_file():
        raise FileNotFoundError(
            f"DEM raster does not exist: {dem_path}"
        )

    if not effective_surface_path.is_file():
        raise FileNotFoundError(
            "Effective surface raster does not exist: "
            f"{effective_surface_path}"
        )

    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if destination_path.exists():
        destination_path.unlink()

    observer_x_m = 0.0
    observer_y_m = 0.0
    observer_clutter_height_m = 0.0
    gdal_observer_height_m = 0.0

    try:
        with (
            rasterio.open(
                dem_path
            ) as dem,
            rasterio.open(
                effective_surface_path
            ) as effective_surface,
        ):
            _validate_aligned_datasets(
                dem,
                effective_surface,
            )

            transformer = (
                Transformer.from_crs(
                    "EPSG:4326",
                    dem.crs,
                    always_xy=True,
                )
            )

            (
                observer_x_m,
                observer_y_m,
            ) = transformer.transform(
                observer_longitude,
                observer_latitude,
            )

            observer_row, observer_col = (
                dem.index(
                    observer_x_m,
                    observer_y_m,
                )
            )

            if (
                observer_row < 0
                or observer_row >= dem.height
                or observer_col < 0
                or observer_col >= dem.width
            ):
                raise ValueError(
                    "Observer location is outside the "
                    "DEM working grid."
                )

            dem_values = dem.read(
                1,
                masked=True,
            )

            effective_values = (
                effective_surface.read(
                    1,
                    masked=True,
                )
            )

            if (
                np.ma.getmaskarray(
                    dem_values
                )[
                    observer_row,
                    observer_col,
                ]
                or np.ma.getmaskarray(
                    effective_values
                )[
                    observer_row,
                    observer_col,
                ]
            ):
                raise ValueError(
                    "Observer location falls on a NoData cell."
                )

            observer_ground_elevation_m = float(
                dem_values[
                    observer_row,
                    observer_col,
                ]
            )

            observer_effective_elevation_m = float(
                effective_values[
                    observer_row,
                    observer_col,
                ]
            )

            observer_clutter_height_m = (
                observer_effective_elevation_m
                - observer_ground_elevation_m
            )

            if (
                observer_clutter_height_m
                < -CLUTTER_HEIGHT_TOLERANCE_M
            ):
                raise ValueError(
                    "Effective surface is below DEM elevation "
                    "at the observer location."
                )

            observer_clutter_height_m = max(
                0.0,
                observer_clutter_height_m,
            )

            gdal_observer_height_m = (
                transmitter_height_agl_m
                - observer_clutter_height_m
            )

            output_profile = (
                dem.profile.copy()
            )

            output_profile.update(
                driver="GTiff",
                dtype="uint8",
                count=1,
                nodata=(
                    VIEWSHED_NODATA_VALUE
                ),
                compress="deflate",
            )

            target_crs = str(
                dem.crs
            )

            width_px = dem.width
            height_px = dem.height

            resolution_x_m = abs(
                float(
                    dem.res[0]
                )
            )

            resolution_y_m = abs(
                float(
                    dem.res[1]
                )
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            minimum_height_path = (
                Path(
                    temp_dir
                )
                / "minimum_target_height.tif"
            )

            command = [
                str(
                    executable
                ),
                "--quiet",
                "-of",
                "GTiff",
                "-ox",
                str(
                    observer_x_m
                ),
                "-oy",
                str(
                    observer_y_m
                ),
                "-oz",
                str(
                    gdal_observer_height_m
                ),
                "-cc",
                str(
                    curvature_coefficient
                ),
                "-om",
                "GROUND",
                "-a_nodata",
                str(
                    DEFAULT_DEM_NODATA
                ),
                "-co",
                "COMPRESS=DEFLATE",
                str(
                    effective_surface_path
                ),
                str(
                    minimum_height_path
                ),
            ]

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
            )

            if completed.returncode != 0:
                raise RuntimeError(
                    "GDAL viewshed failed.\n"
                    f"Command: {' '.join(command)}\n"
                    f"stdout: {completed.stdout}\n"
                    f"stderr: {completed.stderr}"
                )

            if not minimum_height_path.exists():
                raise RuntimeError(
                    "GDAL viewshed completed without creating "
                    "the expected output raster."
                )

            with (
                rasterio.open(
                    dem_path
                ) as dem,
                rasterio.open(
                    effective_surface_path
                ) as effective_surface,
                rasterio.open(
                    minimum_height_path
                ) as minimum_height,
            ):
                _validate_aligned_datasets(
                    dem,
                    effective_surface,
                )

                if minimum_height.crs != dem.crs:
                    raise ValueError(
                        "GDAL viewshed output CRS does not "
                        "match the DEM CRS."
                    )

                if (
                    minimum_height.width != dem.width
                    or minimum_height.height != dem.height
                ):
                    raise ValueError(
                        "GDAL viewshed output dimensions do "
                        "not match the DEM grid."
                    )

                if not _transforms_match(
                    minimum_height.transform,
                    dem.transform,
                ):
                    raise ValueError(
                        "GDAL viewshed output transform does "
                        "not match the DEM grid."
                    )

                dem_values = dem.read(
                    1,
                    masked=True,
                )

                effective_values = (
                    effective_surface.read(
                        1,
                        masked=True,
                    )
                )

                minimum_height_values = (
                    minimum_height.read(
                        1,
                        masked=True,
                    )
                )

                visibility = (
                    build_binary_viewshed_mask(
                        dem_values=dem_values,
                        effective_surface_values=(
                            effective_values
                        ),
                        minimum_target_height_values=(
                            minimum_height_values
                        ),
                        transform=dem.transform,
                        observer_x_m=(
                            observer_x_m
                        ),
                        observer_y_m=(
                            observer_y_m
                        ),
                        receiver_height_agl_m=(
                            receiver_height_agl_m
                        ),
                        calculation_radius_m=(
                            calculation_radius_m
                        ),
                    )
                )

                with rasterio.open(
                    destination_path,
                    "w",
                    **output_profile,
                ) as destination:
                    destination.write(
                        visibility,
                        1,
                    )

                    destination.update_tags(
                        analysis_method=(
                            "terrain_clutter_viewshed"
                        ),
                        gdal_version=(
                            gdal_version
                        ),
                        k_factor=str(
                            k_factor
                        ),
                        curvature_coefficient=str(
                            curvature_coefficient
                        ),
                        transmitter_height_agl_m=str(
                            transmitter_height_agl_m
                        ),
                        receiver_height_agl_m=str(
                            receiver_height_agl_m
                        ),
                        observer_clutter_height_m=str(
                            observer_clutter_height_m
                        ),
                        calculation_radius_m=str(
                            calculation_radius_m
                        ),
                    )

        visible_cell_count = int(
            np.count_nonzero(
                visibility
                == VIEWSHED_VISIBLE_VALUE
            )
        )

        evaluated_cell_count = int(
            np.count_nonzero(
                visibility
                != VIEWSHED_NODATA_VALUE
            )
        )

    except Exception:
        if destination_path.exists():
            destination_path.unlink()

        raise

    return ViewshedResult(
        dem_path=str(
            dem_path
        ),
        effective_surface_path=str(
            effective_surface_path
        ),
        destination_path=str(
            destination_path
        ),
        gdal_viewshed_path=str(
            executable
        ),
        gdal_version=gdal_version,
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
        transmitter_height_agl_m=(
            transmitter_height_agl_m
        ),
        receiver_height_agl_m=(
            receiver_height_agl_m
        ),
        observer_clutter_height_m=(
            observer_clutter_height_m
        ),
        gdal_observer_height_m=(
            gdal_observer_height_m
        ),
        calculation_radius_m=(
            calculation_radius_m
        ),
        k_factor=float(
            k_factor
        ),
        curvature_coefficient=float(
            curvature_coefficient
        ),
        visible_value=(
            VIEWSHED_VISIBLE_VALUE
        ),
        not_visible_value=(
            VIEWSHED_NOT_VISIBLE_VALUE
        ),
        nodata_value=(
            VIEWSHED_NODATA_VALUE
        ),
        visible_cell_count=(
            visible_cell_count
        ),
        evaluated_cell_count=(
            evaluated_cell_count
        ),
    )