"""GeoVaris coverage GeoJSON output.

This module converts the coverage-mask band of a GeoVaris coverage
GeoTIFF into map-ready GeoJSON.

Current MVP behavior:
- Read Band 3 of the coverage GeoTIFF.
- Polygonize only cells whose coverage-mask value is 1.
- Preserve the analytical raster footprint without smoothing.
- Reproject polygon coordinates to EPSG:4326 for web mapping.
- Preserve basic RF model lineage in GeoJSON properties.

Coverage results are engineering estimates and do not guarantee
actual service availability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom


COVERAGE_MASK_BAND = 3
COVERED_VALUE = 1.0
OUTPUT_CRS = "EPSG:4326"


@dataclass(frozen=True)
class CoverageGeoJsonResult:
    """Metadata describing a written coverage GeoJSON file."""

    geojson_path: str

    feature_count: int

    source_crs: str
    output_crs: str

    model_name: str | None
    model_version: str | None


def _validate_raster_path(
    raster_path: str,
) -> Path:
    """Validate the source raster path."""

    path = Path(
        raster_path
    )

    if not path.exists():
        raise FileNotFoundError(
            "Coverage raster does not exist: "
            f"{raster_path}"
        )

    if not path.is_file():
        raise ValueError(
            "Coverage raster path is not a file: "
            f"{raster_path}"
        )

    return path


def _coverage_features(
    *,
    raster_path: Path,
) -> tuple[
    list[dict[str, Any]],
    str,
    dict[str, str],
]:
    """Extract covered-cell polygons from the coverage raster."""

    with rasterio.open(
        raster_path
    ) as dataset:
        if dataset.count < COVERAGE_MASK_BAND:
            raise ValueError(
                "Coverage raster must contain at least "
                f"{COVERAGE_MASK_BAND} bands."
            )

        if dataset.crs is None:
            raise ValueError(
                "Coverage raster does not define a CRS."
            )

        coverage_mask = dataset.read(
            COVERAGE_MASK_BAND
        )

        covered_cells = np.isclose(
            coverage_mask,
            COVERED_VALUE,
            rtol=0.0,
            atol=1e-6,
        )

        if not np.any(
            covered_cells
        ):
            raise ValueError(
                "Coverage raster contains no covered cells."
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

        polygon_iterator = shapes(
            coverage_mask,
            mask=covered_cells,
            transform=dataset.transform,
            connectivity=4,
        )

        for geometry, value in polygon_iterator:
            if not np.isclose(
                float(value),
                COVERED_VALUE,
                rtol=0.0,
                atol=1e-6,
            ):
                continue

            transformed_geometry = (
                transform_geom(
                    source_crs,
                    OUTPUT_CRS,
                    geometry,
                    precision=7,
                )
            )

            feature = {
                "type": "Feature",
                "properties": {
                    "coverage": True,
                    "coverage_value": 1,
                    "engineering_estimate": True,
                    "model_name": (
                        dataset_tags.get(
                            "model_name"
                        )
                    ),
                    "model_version": (
                        dataset_tags.get(
                            "model_version"
                        )
                    ),
                    "source_crs": (
                        source_crs
                    ),
                    "output_crs": (
                        OUTPUT_CRS
                    ),
                },
                "geometry": (
                    transformed_geometry
                ),
            }

            features.append(
                feature
            )

    return (
        features,
        source_crs,
        dataset_tags,
    )


def coverage_raster_to_geojson(
    *,
    raster_path: str,
    output_path: str,
) -> CoverageGeoJsonResult:
    """Convert a GeoVaris coverage raster to GeoJSON."""

    source_path = (
        _validate_raster_path(
            raster_path
        )
    )

    features, source_crs, tags = (
        _coverage_features(
            raster_path=source_path
        )
    )

    output = Path(
        output_path
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_collection = {
        "type": "FeatureCollection",
        "name": "GeoVaris Coverage Footprint",
        "properties": {
            "product": (
                "GeoVaris Coverage Intelligence"
            ),
            "engineering_estimate": True,
            "source_raster": (
                source_path.name
            ),
            "source_crs": (
                source_crs
            ),
            "output_crs": (
                OUTPUT_CRS
            ),
            "model_name": (
                tags.get(
                    "model_name"
                )
            ),
            "model_version": (
                tags.get(
                    "model_version"
                )
            ),
        },
        "features": features,
    }

    output.write_text(
        json.dumps(
            feature_collection,
            indent=2,
        ),
        encoding="utf-8",
    )

    return CoverageGeoJsonResult(
        geojson_path=str(
            output.resolve()
        ),
        feature_count=len(
            features
        ),
        source_crs=source_crs,
        output_crs=OUTPUT_CRS,
        model_name=(
            tags.get(
                "model_name"
            )
        ),
        model_version=(
            tags.get(
                "model_version"
            )
        ),
    )