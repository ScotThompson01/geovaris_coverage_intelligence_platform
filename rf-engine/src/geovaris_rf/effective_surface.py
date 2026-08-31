"""Effective obstruction surface generation for GeoVaris Coverage Intelligence.

The Rapid Coverage Estimate uses an effective obstruction surface:

    effective elevation =
        bare-earth DEM elevation
        + governed clutter height

The DEM remains the terrain source of record. Annual NLCD remains the
land-cover source of record. This module derives a separate raster by
reprojecting NLCD land-cover classes onto the DEM working grid using
nearest-neighbor resampling and applying a versioned clutter-height
profile.

Important distinctions:
- NLCD classes are land-cover classifications, not measured heights.
- Clutter heights are governed engineering planning assumptions.
- P.2108 statistical clutter loss is separate from this process.
- The original DEM is never modified.

RF results are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from geovaris_rf.clutter import (
    NLCD_NODATA_VALUE,
    validate_nlcd_raster,
)
from geovaris_rf.clutter_height import (
    ClutterHeightProfile,
)
from geovaris_rf.dem_raster import (
    DEFAULT_DEM_NODATA,
)


@dataclass(frozen=True)
class EffectiveSurfaceResult:
    """Metadata describing one derived effective obstruction surface."""

    dem_path: str
    clutter_raster_path: str
    destination_path: str

    target_crs: str
    resolution_x_m: float
    resolution_y_m: float
    width_px: int
    height_px: int

    nodata: float

    clutter_profile_name: str
    clutter_profile_version: str
    clutter_profile_source: str
    clutter_height_units: str

    minimum_clutter_height_m: float
    maximum_clutter_height_m: float


def _resolve_input_file(
    path_value: str | Path,
    *,
    name: str,
) -> Path:
    """Resolve and validate one required input file."""

    path = Path(
        path_value
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"{name} does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"{name} is not a file: {path}"
        )

    return path


def _resolve_destination_file(
    path_value: str | Path,
) -> Path:
    """Resolve destination path and create its parent directory."""

    path = Path(
        path_value
    ).expanduser().resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


def _validate_dem_dataset(
    dataset: rasterio.io.DatasetReader,
    *,
    dem_path: Path,
) -> None:
    """Validate the DEM requirements for effective-surface generation."""

    if dataset.count != 1:
        raise ValueError(
            "DEM raster must contain exactly one band; "
            f"got {dataset.count}: {dem_path}"
        )

    if dataset.crs is None:
        raise ValueError(
            f"DEM raster does not define a CRS: {dem_path}"
        )

    if not dataset.crs.is_projected:
        raise ValueError(
            "DEM raster must use a projected CRS for the RF "
            f"working grid: {dem_path}"
        )

    if dataset.width <= 0 or dataset.height <= 0:
        raise ValueError(
            f"DEM raster dimensions are invalid: {dem_path}"
        )

    resolution_x_m = abs(
        float(
            dataset.res[0]
        )
    )

    resolution_y_m = abs(
        float(
            dataset.res[1]
        )
    )

    if resolution_x_m <= 0 or resolution_y_m <= 0:
        raise ValueError(
            f"DEM raster resolution is invalid: {dem_path}"
        )


def build_clutter_height_array(
    *,
    nlcd_values: np.ndarray,
    profile: ClutterHeightProfile,
    nlcd_nodata_value: int = NLCD_NODATA_VALUE,
) -> np.ma.MaskedArray:
    """Convert NLCD class values into governed clutter heights.

    The returned masked array has the same shape as ``nlcd_values``.

    NLCD NoData cells are masked.

    Any other NLCD class without an explicit profile entry causes the
    operation to fail. GeoVaris does not silently assign zero clutter
    height to unknown land-cover classes.
    """

    values = np.asarray(
        nlcd_values
    )

    if values.ndim != 2:
        raise ValueError(
            "NLCD values must be a two-dimensional array."
        )

    if not np.issubdtype(
        values.dtype,
        np.integer,
    ):
        raise ValueError(
            "NLCD values must use an integer data type."
        )

    nodata_mask = (
        values
        == int(
            nlcd_nodata_value
        )
    )

    lookup = np.full(
        256,
        np.nan,
        dtype=np.float32,
    )

    for (
        class_value,
        clutter_class,
    ) in profile.classes.items():
        if (
            class_value < 0
            or class_value > 255
        ):
            raise ValueError(
                "NLCD class values must fit within uint8 range; "
                f"got {class_value}."
            )

        lookup[
            class_value
        ] = np.float32(
            clutter_class.height_m
        )

    valid_values = values[
        ~nodata_mask
    ]

    if valid_values.size:
        minimum_value = int(
            valid_values.min()
        )

        maximum_value = int(
            valid_values.max()
        )

        if (
            minimum_value < 0
            or maximum_value > 255
        ):
            raise ValueError(
                "NLCD raster contains class values outside "
                "the supported uint8 range."
            )

        mapped_values = lookup[
            valid_values
        ]

        unsupported_mask = np.isnan(
            mapped_values
        )

        if np.any(
            unsupported_mask
        ):
            unsupported_values = sorted(
                {
                    int(value)
                    for value in valid_values[
                        unsupported_mask
                    ]
                }
            )

            raise ValueError(
                "NLCD raster contains unsupported land-cover "
                "class values: "
                + ", ".join(
                    str(value)
                    for value in unsupported_values
                )
                + "."
            )

    height_array = np.zeros(
        values.shape,
        dtype=np.float32,
    )

    non_nodata_mask = (
        ~nodata_mask
    )

    height_array[
        non_nodata_mask
    ] = lookup[
        values[
            non_nodata_mask
        ]
    ]

    return np.ma.array(
        height_array,
        mask=nodata_mask,
    )


def build_effective_surface_raster(
    *,
    dem_path: str | Path,
    clutter_raster_path: str | Path,
    destination_path: str | Path,
    clutter_profile: ClutterHeightProfile,
) -> EffectiveSurfaceResult:
    """Create a DEM + governed clutter-height obstruction raster.

    Processing:
    1. Open and validate the RF working-grid DEM.
    2. Validate the source Annual NLCD raster.
    3. Reproject NLCD classes to the exact DEM grid using nearest
       neighbor resampling.
    4. Convert aligned NLCD classes to governed clutter heights.
    5. Add clutter heights to valid DEM cells.
    6. Write a separate float32 GeoTIFF using the DEM grid exactly.

    A cell becomes NoData if either:
    - the DEM cell is NoData, or
    - the aligned NLCD cell is NoData.

    Unknown NLCD class values cause the operation to fail rather than
    silently receiving zero clutter height.
    """

    source_dem = _resolve_input_file(
        dem_path,
        name="DEM raster",
    )

    source_clutter = _resolve_input_file(
        clutter_raster_path,
        name="Clutter raster",
    )

    destination = _resolve_destination_file(
        destination_path
    )

    validate_nlcd_raster(
        source_clutter
    )

    try:
        with rasterio.open(
            source_dem
        ) as dem:
            _validate_dem_dataset(
                dem,
                dem_path=source_dem,
            )

            dem_values = dem.read(
                1,
                masked=True,
            )

            aligned_nlcd = np.full(
                (
                    dem.height,
                    dem.width,
                ),
                NLCD_NODATA_VALUE,
                dtype=np.uint8,
            )

            with rasterio.open(
                source_clutter
            ) as clutter:
                reproject(
                    source=rasterio.band(
                        clutter,
                        1,
                    ),
                    destination=aligned_nlcd,
                    src_transform=(
                        clutter.transform
                    ),
                    src_crs=(
                        clutter.crs
                    ),
                    src_nodata=(
                        clutter.nodata
                    ),
                    dst_transform=(
                        dem.transform
                    ),
                    dst_crs=(
                        dem.crs
                    ),
                    dst_nodata=(
                        NLCD_NODATA_VALUE
                    ),
                    resampling=(
                        Resampling.nearest
                    ),
                )

            clutter_heights = (
                build_clutter_height_array(
                    nlcd_values=aligned_nlcd,
                    profile=clutter_profile,
                )
            )

            dem_mask = np.ma.getmaskarray(
                dem_values
            )

            clutter_mask = np.ma.getmaskarray(
                clutter_heights
            )

            combined_mask = (
                dem_mask
                | clutter_mask
            )

            dem_data = np.asarray(
                dem_values.filled(
                    DEFAULT_DEM_NODATA
                ),
                dtype=np.float32,
            )

            clutter_data = np.asarray(
                clutter_heights.filled(
                    0.0
                ),
                dtype=np.float32,
            )

            effective_surface = (
                dem_data
                + clutter_data
            ).astype(
                np.float32
            )

            effective_surface[
                combined_mask
            ] = np.float32(
                DEFAULT_DEM_NODATA
            )

            valid_clutter_heights = (
                clutter_data[
                    ~combined_mask
                ]
            )

            if valid_clutter_heights.size == 0:
                raise ValueError(
                    "Effective surface contains no valid "
                    "DEM + clutter cells."
                )

            minimum_clutter_height_m = float(
                valid_clutter_heights.min()
            )

            maximum_clutter_height_m = float(
                valid_clutter_heights.max()
            )

            profile = dem.profile.copy()

            profile.update(
                driver="GTiff",
                dtype="float32",
                count=1,
                crs=dem.crs,
                transform=dem.transform,
                width=dem.width,
                height=dem.height,
                nodata=DEFAULT_DEM_NODATA,
                compress="deflate",
            )

            with rasterio.open(
                destination,
                "w",
                **profile,
            ) as output:
                output.write(
                    effective_surface,
                    1,
                )

            result = EffectiveSurfaceResult(
                dem_path=str(
                    source_dem
                ),
                clutter_raster_path=str(
                    source_clutter
                ),
                destination_path=str(
                    destination
                ),
                target_crs=str(
                    dem.crs
                ),
                resolution_x_m=abs(
                    float(
                        dem.res[0]
                    )
                ),
                resolution_y_m=abs(
                    float(
                        dem.res[1]
                    )
                ),
                width_px=dem.width,
                height_px=dem.height,
                nodata=DEFAULT_DEM_NODATA,
                clutter_profile_name=(
                    clutter_profile.name
                ),
                clutter_profile_version=(
                    clutter_profile.version
                ),
                clutter_profile_source=(
                    clutter_profile.source
                ),
                clutter_height_units=(
                    clutter_profile.units
                ),
                minimum_clutter_height_m=(
                    minimum_clutter_height_m
                ),
                maximum_clutter_height_m=(
                    maximum_clutter_height_m
                ),
            )

    except Exception:
        if destination.exists():
            destination.unlink()

        raise

    return result