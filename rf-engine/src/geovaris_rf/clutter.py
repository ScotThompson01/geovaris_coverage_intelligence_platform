"""GeoVaris land-cover / clutter data adapter.

This module interprets Annual NLCD land-cover raster classes and maps them
into normalized GeoVaris clutter categories.

It does NOT apply RF attenuation.

Clutter attenuation, effective heights, and other RF assumptions must remain
separate, configurable engineering inputs so that land-cover classification
is not confused with propagation loss.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from pathlib import Path

import rasterio
from pyproj import Transformer


EXPECTED_NLCD_RESOLUTION_M = 30.0
NLCD_NODATA_VALUE = 250


class NlcdLandCoverClass(IntEnum):
    """Annual NLCD land-cover class values."""

    OPEN_WATER = 11

    DEVELOPED_OPEN_SPACE = 21
    DEVELOPED_LOW_INTENSITY = 22
    DEVELOPED_MEDIUM_INTENSITY = 23
    DEVELOPED_HIGH_INTENSITY = 24

    BARREN_LAND = 31

    DECIDUOUS_FOREST = 41
    EVERGREEN_FOREST = 42
    MIXED_FOREST = 43

    SHRUB_SCRUB = 52

    GRASSLAND_HERBACEOUS = 71

    PASTURE_HAY = 81
    CULTIVATED_CROPS = 82

    WOODY_WETLANDS = 90
    EMERGENT_HERBACEOUS_WETLANDS = 95


class GeoVarisClutterClass(StrEnum):
    """Normalized GeoVaris clutter categories.

    These are classification categories only.

    No RF loss or effective-height values are implied by the enum.
    """

    WATER = "water"
    OPEN = "open"
    AGRICULTURE = "agriculture"

    DEVELOPED_OPEN = "developed_open"
    SUBURBAN = "suburban"
    DENSE_SUBURBAN = "dense_suburban"
    URBAN = "urban"

    FOREST = "forest"
    WETLAND = "wetland"


NLCD_TO_GEOVARIS_CLUTTER = {
    NlcdLandCoverClass.OPEN_WATER:
        GeoVarisClutterClass.WATER,

    NlcdLandCoverClass.DEVELOPED_OPEN_SPACE:
        GeoVarisClutterClass.DEVELOPED_OPEN,

    NlcdLandCoverClass.DEVELOPED_LOW_INTENSITY:
        GeoVarisClutterClass.SUBURBAN,

    NlcdLandCoverClass.DEVELOPED_MEDIUM_INTENSITY:
        GeoVarisClutterClass.DENSE_SUBURBAN,

    NlcdLandCoverClass.DEVELOPED_HIGH_INTENSITY:
        GeoVarisClutterClass.URBAN,

    NlcdLandCoverClass.BARREN_LAND:
        GeoVarisClutterClass.OPEN,

    NlcdLandCoverClass.DECIDUOUS_FOREST:
        GeoVarisClutterClass.FOREST,

    NlcdLandCoverClass.EVERGREEN_FOREST:
        GeoVarisClutterClass.FOREST,

    NlcdLandCoverClass.MIXED_FOREST:
        GeoVarisClutterClass.FOREST,

    NlcdLandCoverClass.SHRUB_SCRUB:
        GeoVarisClutterClass.OPEN,

    NlcdLandCoverClass.GRASSLAND_HERBACEOUS:
        GeoVarisClutterClass.OPEN,

    NlcdLandCoverClass.PASTURE_HAY:
        GeoVarisClutterClass.AGRICULTURE,

    NlcdLandCoverClass.CULTIVATED_CROPS:
        GeoVarisClutterClass.AGRICULTURE,

    NlcdLandCoverClass.WOODY_WETLANDS:
        GeoVarisClutterClass.WETLAND,

    NlcdLandCoverClass.EMERGENT_HERBACEOUS_WETLANDS:
        GeoVarisClutterClass.WETLAND,
}


@dataclass(frozen=True)
class ClutterRasterMetadata:
    """Validated metadata for a clutter raster."""

    raster_path: str
    crs: str
    width: int
    height: int
    resolution_x_m: float
    resolution_y_m: float
    nodata_value: float | None
    band_count: int
    dtype: str


@dataclass(frozen=True)
class ClutterSample:
    """Land-cover sample at one geographic location."""

    latitude: float
    longitude: float

    source_class_value: int
    source_class: NlcdLandCoverClass

    clutter_class: GeoVarisClutterClass


def validate_nlcd_raster(
    raster_path: str | Path,
) -> ClutterRasterMetadata:
    """Validate an Annual NLCD land-cover raster."""

    path = Path(
        raster_path
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"Clutter raster does not exist: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Clutter raster path is not a file: {path}"
        )

    with rasterio.open(
        path
    ) as dataset:
        if dataset.count != 1:
            raise ValueError(
                "NLCD clutter raster must contain exactly one band; "
                f"got {dataset.count}."
            )

        if dataset.crs is None:
            raise ValueError(
                "NLCD clutter raster does not define a CRS."
            )

        if not dataset.crs.is_projected:
            raise ValueError(
                "NLCD clutter raster must use a projected CRS."
            )

        x_resolution_m = abs(
            float(
                dataset.res[0]
            )
        )

        y_resolution_m = abs(
            float(
                dataset.res[1]
            )
        )

        if abs(
            x_resolution_m
            - EXPECTED_NLCD_RESOLUTION_M
        ) > 1e-6:
            raise ValueError(
                "Unexpected NLCD X resolution: "
                f"{x_resolution_m} m."
            )

        if abs(
            y_resolution_m
            - EXPECTED_NLCD_RESOLUTION_M
        ) > 1e-6:
            raise ValueError(
                "Unexpected NLCD Y resolution: "
                f"{y_resolution_m} m."
            )

        if dataset.dtypes[0] != "uint8":
            raise ValueError(
                "NLCD clutter raster must use uint8 values; "
                f"got {dataset.dtypes[0]}."
            )

        if (
            dataset.nodata is None
            or int(
                dataset.nodata
            ) != NLCD_NODATA_VALUE
        ):
            raise ValueError(
                "Expected Annual NLCD NoData value "
                f"{NLCD_NODATA_VALUE}; got {dataset.nodata}."
            )

        return ClutterRasterMetadata(
            raster_path=str(
                path
            ),
            crs=str(
                dataset.crs
            ),
            width=dataset.width,
            height=dataset.height,
            resolution_x_m=x_resolution_m,
            resolution_y_m=y_resolution_m,
            nodata_value=dataset.nodata,
            band_count=dataset.count,
            dtype=dataset.dtypes[0],
        )


def nlcd_class_to_clutter(
    class_value: int,
) -> tuple[
    NlcdLandCoverClass,
    GeoVarisClutterClass,
]:
    """Convert an NLCD class code into a GeoVaris clutter category."""

    try:
        nlcd_class = (
            NlcdLandCoverClass(
                int(
                    class_value
                )
            )
        )
    except ValueError as exc:
        raise ValueError(
            "Unsupported NLCD land-cover class: "
            f"{class_value}."
        ) from exc

    return (
        nlcd_class,
        NLCD_TO_GEOVARIS_CLUTTER[
            nlcd_class
        ],
    )


def sample_clutter(
    *,
    raster_path: str | Path,
    latitude: float,
    longitude: float,
) -> ClutterSample:
    """Sample an NLCD clutter raster at latitude/longitude."""

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"Invalid latitude: {latitude}."
        )

    if not -180.0 <= longitude <= 180.0:
        raise ValueError(
            f"Invalid longitude: {longitude}."
        )

    validate_nlcd_raster(
        raster_path
    )

    path = Path(
        raster_path
    ).expanduser().resolve()

    with rasterio.open(
        path
    ) as dataset:
        transformer = (
            Transformer.from_crs(
                "EPSG:4326",
                dataset.crs,
                always_xy=True,
            )
        )

        x_m, y_m = transformer.transform(
            longitude,
            latitude,
        )

        bounds = dataset.bounds

        if not (
            bounds.left
            <= x_m
            <= bounds.right
            and bounds.bottom
            <= y_m
            <= bounds.top
        ):
            raise ValueError(
                "Requested clutter sample is outside "
                "the raster extent."
            )

        value = next(
            dataset.sample(
                [
                    (
                        x_m,
                        y_m,
                    )
                ]
            )
        )[0]

        class_value = int(
            value
        )

        if class_value == NLCD_NODATA_VALUE:
            raise ValueError(
                "Requested clutter sample is NoData."
            )

    (
        source_class,
        clutter_class,
    ) = nlcd_class_to_clutter(
        class_value
    )

    return ClutterSample(
        latitude=latitude,
        longitude=longitude,
        source_class_value=class_value,
        source_class=source_class,
        clutter_class=clutter_class,
    )
    