"""GeoJSON output for GeoVaris Rapid Coverage Estimate rasters.

This module converts a single-band Rapid Coverage Estimate GeoTIFF
into map-ready GeoJSON.

Rapid raster convention:

    1   estimated covered
    0   not estimated covered
    255 NoData

Two concepts are deliberately kept separate:

Authoritative analytics
    The full analytical coverage raster remains the source of truth
    for area, population, Fabric, and other coverage analytics.

Display footprint
    Small disconnected coverage components may be omitted from a
    display-oriented GeoJSON export to reduce browser payload size.

Display filtering must never change the authoritative raster-derived
coverage area stored for the coverage run.

The output represents an engineering estimate and does not guarantee
actual service availability.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom

from geovaris_rf.rapid_coverage import (
    RAPID_COVERAGE_COVERED_VALUE,
    RAPID_COVERAGE_NODATA_VALUE,
)


OUTPUT_CRS = "EPSG:4326"

SQUARE_METERS_PER_SQUARE_KILOMETER = 1_000_000.0
SQUARE_METERS_PER_SQUARE_MILE = 2_589_988.110336

DEFAULT_DISPLAY_MINIMUM_COMPONENT_AREA_M2 = 900.0
DEFAULT_DISPLAY_COORDINATE_PRECISION = 6


@dataclass(frozen=True)
class RapidCoverageGeoJsonResult:
    """Metadata describing one Rapid Coverage GeoJSON export."""

    geojson_path: str

    feature_count: int
    covered_cell_count: int

    authoritative_covered_area_m2: float
    authoritative_covered_area_km2: float
    authoritative_covered_area_mi2: float

    display_retained_area_m2: float
    display_retained_area_km2: float
    display_retained_area_percent: float

    minimum_component_area_m2: float
    coordinate_precision: int

    source_crs: str
    output_crs: str

    analysis_method: str | None
    methodology: str | None

    source_raster: str


def _validate_raster_path(
    raster_path: str | Path,
) -> Path:
    """Validate the source Rapid Coverage raster path."""

    path = Path(
        raster_path
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            "Rapid Coverage raster does not exist: "
            f"{path}"
        )

    if not path.is_file():
        raise ValueError(
            "Rapid Coverage raster path is not a file: "
            f"{path}"
        )

    return path


def _validate_rapid_raster(
    dataset: rasterio.io.DatasetReader,
) -> None:
    """Validate a Rapid Coverage raster before polygonization."""

    if dataset.count != 1:
        raise ValueError(
            "Rapid Coverage raster must contain exactly one band."
        )

    if dataset.crs is None:
        raise ValueError(
            "Rapid Coverage raster does not define a CRS."
        )

    if not dataset.crs.is_projected:
        raise ValueError(
            "Rapid Coverage raster must use a projected CRS."
        )

    if dataset.width <= 0 or dataset.height <= 0:
        raise ValueError(
            "Rapid Coverage raster dimensions must be greater than zero."
        )

    resolution_x = abs(
        float(
            dataset.res[0]
        )
    )

    resolution_y = abs(
        float(
            dataset.res[1]
        )
    )

    if (
        not math.isfinite(
            resolution_x
        )
        or not math.isfinite(
            resolution_y
        )
        or resolution_x <= 0
        or resolution_y <= 0
    ):
        raise ValueError(
            "Rapid Coverage raster resolution must be finite "
            "and greater than zero."
        )


def _validate_display_options(
    *,
    minimum_component_area_m2: float,
    coordinate_precision: int,
) -> tuple[float, int]:
    """Validate display-export filtering options."""

    minimum_component_area_m2 = float(
        minimum_component_area_m2
    )

    if (
        not math.isfinite(
            minimum_component_area_m2
        )
        or minimum_component_area_m2 < 0
    ):
        raise ValueError(
            "minimum_component_area_m2 must be finite "
            "and zero or greater."
        )

    if isinstance(
        coordinate_precision,
        bool,
    ):
        raise ValueError(
            "coordinate_precision must be an integer."
        )

    coordinate_precision = int(
        coordinate_precision
    )

    if (
        coordinate_precision < 0
        or coordinate_precision > 15
    ):
        raise ValueError(
            "coordinate_precision must be between 0 and 15."
        )

    return (
        minimum_component_area_m2,
        coordinate_precision,
    )


def _ring_area_m2(
    ring: list[list[float]],
) -> float:
    """Return absolute planar area of one closed ring."""

    signed_area = 0.0

    for index in range(
        len(ring) - 1
    ):
        x1, y1 = ring[
            index
        ]

        x2, y2 = ring[
            index + 1
        ]

        signed_area += (
            x1 * y2
            - x2 * y1
        )

    return abs(
        signed_area
    ) / 2.0


def _polygon_area_m2(
    rings: list[list[list[float]]],
) -> float:
    """Return polygon area with interior holes removed."""

    if not rings:
        return 0.0

    exterior_area = _ring_area_m2(
        rings[0]
    )

    hole_area = sum(
        _ring_area_m2(
            ring
        )
        for ring in rings[1:]
    )

    return max(
        0.0,
        exterior_area - hole_area,
    )


def _geometry_area_m2(
    geometry: dict[str, Any],
) -> float:
    """Return planar area for Polygon or MultiPolygon geometry."""

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if not isinstance(
        coordinates,
        list,
    ):
        raise ValueError(
            "Coverage geometry has invalid coordinates."
        )

    if geometry_type == "Polygon":
        return _polygon_area_m2(
            coordinates
        )

    if geometry_type == "MultiPolygon":
        return sum(
            _polygon_area_m2(
                polygon
            )
            for polygon in coordinates
        )

    raise ValueError(
        "Unsupported coverage geometry type: "
        f"{geometry_type!r}."
    )


def _rapid_coverage_features(
    *,
    raster_path: Path,
    minimum_component_area_m2: float,
    coordinate_precision: int,
) -> tuple[
    list[dict[str, Any]],
    str,
    dict[str, str],
    int,
    float,
    float,
]:
    """Extract display polygons and authoritative area metadata."""

    with rasterio.open(
        raster_path
    ) as dataset:
        _validate_rapid_raster(
            dataset
        )

        coverage = dataset.read(
            1,
            masked=True,
        )

        source_mask = (
            np.ma.getmaskarray(
                coverage
            )
        )

        coverage_data = np.asarray(
            coverage.filled(
                RAPID_COVERAGE_NODATA_VALUE
            ),
            dtype=np.uint8,
        )

        valid_values = coverage_data[
            ~source_mask
        ]

        if valid_values.size:
            supported_values = np.isin(
                valid_values,
                [
                    0,
                    RAPID_COVERAGE_COVERED_VALUE,
                ],
            )

            if not bool(
                np.all(
                    supported_values
                )
            ):
                raise ValueError(
                    "Rapid Coverage raster contains unsupported values."
                )

        covered_cells = (
            ~source_mask
            & (
                coverage_data
                == RAPID_COVERAGE_COVERED_VALUE
            )
        )

        covered_cell_count = int(
            np.count_nonzero(
                covered_cells
            )
        )

        if covered_cell_count == 0:
            raise ValueError(
                "Rapid Coverage raster contains no covered cells."
            )

        cell_area_m2 = (
            abs(
                float(
                    dataset.res[0]
                )
            )
            * abs(
                float(
                    dataset.res[1]
                )
            )
        )

        authoritative_covered_area_m2 = (
            covered_cell_count
            * cell_area_m2
        )

        source_crs = (
            dataset.crs.to_string()
        )

        dataset_tags = (
            dataset.tags()
        )

        features: list[
            dict[str, Any]
        ] = []

        display_retained_area_m2 = 0.0

        polygon_iterator = shapes(
            coverage_data,
            mask=covered_cells,
            transform=dataset.transform,
            connectivity=4,
        )

        for geometry, value in polygon_iterator:
            if (
                int(
                    value
                )
                != RAPID_COVERAGE_COVERED_VALUE
            ):
                continue

            component_area_m2 = (
                _geometry_area_m2(
                    geometry
                )
            )

            if (
                component_area_m2 + 1e-6
                < minimum_component_area_m2
            ):
                continue

            transformed_geometry = (
                transform_geom(
                    source_crs,
                    OUTPUT_CRS,
                    geometry,
                    precision=(
                        coordinate_precision
                    ),
                )
            )

            feature = {
                "type": "Feature",
                "properties": {},
                "geometry": (
                    transformed_geometry
                ),
            }

            features.append(
                feature
            )

            display_retained_area_m2 += (
                component_area_m2
            )

    if not features:
        raise ValueError(
            "Display filtering removed all covered components."
        )

    return (
        features,
        source_crs,
        dataset_tags,
        covered_cell_count,
        authoritative_covered_area_m2,
        display_retained_area_m2,
    )


def rapid_coverage_raster_to_geojson(
    *,
    raster_path: str | Path,
    output_path: str | Path,
    minimum_component_area_m2: float = (
        DEFAULT_DISPLAY_MINIMUM_COMPONENT_AREA_M2
    ),
    coordinate_precision: int = (
        DEFAULT_DISPLAY_COORDINATE_PRECISION
    ),
) -> RapidCoverageGeoJsonResult:
    """Convert one Rapid Coverage raster into display GeoJSON.

    The authoritative area values in the returned result and GeoJSON
    properties are always calculated from the source raster.

    Display filtering affects only the exported vector geometry.
    """

    (
        minimum_component_area_m2,
        coordinate_precision,
    ) = _validate_display_options(
        minimum_component_area_m2=(
            minimum_component_area_m2
        ),
        coordinate_precision=(
            coordinate_precision
        ),
    )

    source_path = (
        _validate_raster_path(
            raster_path
        )
    )

    (
        features,
        source_crs,
        tags,
        covered_cell_count,
        authoritative_covered_area_m2,
        display_retained_area_m2,
    ) = _rapid_coverage_features(
        raster_path=source_path,
        minimum_component_area_m2=(
            minimum_component_area_m2
        ),
        coordinate_precision=(
            coordinate_precision
        ),
    )

    authoritative_covered_area_km2 = (
        authoritative_covered_area_m2
        / SQUARE_METERS_PER_SQUARE_KILOMETER
    )

    authoritative_covered_area_mi2 = (
        authoritative_covered_area_m2
        / SQUARE_METERS_PER_SQUARE_MILE
    )

    display_retained_area_km2 = (
        display_retained_area_m2
        / SQUARE_METERS_PER_SQUARE_KILOMETER
    )

    display_retained_area_percent = (
        100.0
        * display_retained_area_m2
        / authoritative_covered_area_m2
    )

    output = Path(
        output_path
    ).expanduser().resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_collection = {
        "type": "FeatureCollection",
        "name": "GeoVaris Rapid Coverage Estimate",
        "properties": {
            "product": (
                "GeoVaris Coverage Intelligence"
            ),
            "engineering_estimate": True,
            "display_geometry": True,
            "analysis_method": (
                tags.get(
                    "analysis_method"
                )
            ),
            "methodology": (
                tags.get(
                    "methodology"
                )
            ),
            "source_raster": (
                source_path.name
            ),
            "source_crs": (
                source_crs
            ),
            "output_crs": (
                OUTPUT_CRS
            ),
            "covered_cell_count": (
                covered_cell_count
            ),
            "authoritative_covered_area_m2": (
                authoritative_covered_area_m2
            ),
            "authoritative_covered_area_km2": (
                authoritative_covered_area_km2
            ),
            "authoritative_covered_area_mi2": (
                authoritative_covered_area_mi2
            ),
            "display_retained_area_m2": (
                display_retained_area_m2
            ),
            "display_retained_area_km2": (
                display_retained_area_km2
            ),
            "display_retained_area_percent": (
                display_retained_area_percent
            ),
            "minimum_component_area_m2": (
                minimum_component_area_m2
            ),
            "coordinate_precision": (
                coordinate_precision
            ),
        },
        "features": (
            features
        ),
    }

    try:
        output.write_text(
            json.dumps(
                feature_collection,
                separators=(
                    ",",
                    ":",
                ),
            ),
            encoding="utf-8",
        )

    except Exception:
        if output.exists():
            output.unlink()

        raise

    return RapidCoverageGeoJsonResult(
        geojson_path=str(
            output
        ),
        feature_count=len(
            features
        ),
        covered_cell_count=(
            covered_cell_count
        ),
        authoritative_covered_area_m2=float(
            authoritative_covered_area_m2
        ),
        authoritative_covered_area_km2=float(
            authoritative_covered_area_km2
        ),
        authoritative_covered_area_mi2=float(
            authoritative_covered_area_mi2
        ),
        display_retained_area_m2=float(
            display_retained_area_m2
        ),
        display_retained_area_km2=float(
            display_retained_area_km2
        ),
        display_retained_area_percent=float(
            display_retained_area_percent
        ),
        minimum_component_area_m2=(
            minimum_component_area_m2
        ),
        coordinate_precision=(
            coordinate_precision
        ),
        source_crs=(
            source_crs
        ),
        output_crs=(
            OUTPUT_CRS
        ),
        analysis_method=(
            tags.get(
                "analysis_method"
            )
        ),
        methodology=(
            tags.get(
                "methodology"
            )
        ),
        source_raster=(
            source_path.name
        ),
    )