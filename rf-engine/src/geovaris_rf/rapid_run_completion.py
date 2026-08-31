"""Database completion helpers for GeoVaris Rapid Coverage runs.

This module stores completed Rapid Coverage Estimate results in the
existing coverage_runs table.

Important separation:

coverage_area_sq_m
    Authoritative analytical area derived from the Rapid raster.

coverage_geometry
    Display-oriented geometry derived from the filtered Rapid GeoJSON.

The display geometry may omit very small disconnected components.
Therefore coverage_area_sq_m must never be recalculated from
coverage_geometry for Rapid Coverage runs.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import psycopg


RAPID_PROPAGATION_MODEL = "rapid_coverage"
RAPID_PROPAGATION_MODEL_VERSION = "demo-2026.1"


def _validate_positive_finite(
    value: float,
    *,
    name: str,
) -> float:
    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value <= 0
    ):
        raise ValueError(
            f"{name} must be finite and greater than zero."
        )

    return numeric_value


def _validate_nonnegative_finite(
    value: float,
    *,
    name: str,
) -> float:
    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value < 0
    ):
        raise ValueError(
            f"{name} must be finite and zero or greater."
        )

    return numeric_value


def _load_feature_collection(
    geojson_path: str | Path,
) -> dict[str, Any]:
    """Load and validate a Rapid display FeatureCollection."""

    path = Path(
        geojson_path
    ).expanduser().resolve()

    if not path.is_file():
        raise FileNotFoundError(
            "Rapid display GeoJSON does not exist: "
            f"{path}"
        )

    document = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if document.get(
        "type"
    ) != "FeatureCollection":
        raise ValueError(
            "Rapid display GeoJSON must be a FeatureCollection."
        )

    features = document.get(
        "features"
    )

    if (
        not isinstance(
            features,
            list,
        )
        or len(
            features
        )
        == 0
    ):
        raise ValueError(
            "Rapid display GeoJSON must contain at least one feature."
        )

    for feature in features:
        if not isinstance(
            feature,
            dict,
        ):
            raise ValueError(
                "Rapid display GeoJSON contains an invalid feature."
            )

        if feature.get(
            "type"
        ) != "Feature":
            raise ValueError(
                "Rapid display GeoJSON contains a non-Feature item."
            )

        geometry = feature.get(
            "geometry"
        )

        if not isinstance(
            geometry,
            dict,
        ):
            raise ValueError(
                "Rapid display GeoJSON feature is missing geometry."
            )

        if geometry.get(
            "type"
        ) not in (
            "Polygon",
            "MultiPolygon",
        ):
            raise ValueError(
                "Rapid display GeoJSON contains unsupported geometry."
            )

    return document


def complete_rapid_run(
    connection: psycopg.Connection,
    *,
    run_id: Any,
    coverage_raster_uri: str,
    display_geojson_path: str | Path,
    authoritative_coverage_area_sq_m: float,
    processing_time_seconds: float,
) -> None:
    """Store a completed Rapid Coverage result.

    Display features are dissolved in PostGIS.

    The authoritative area comes directly from raster analytics and is
    stored separately from the display geometry.
    """

    coverage_raster_uri = str(
        coverage_raster_uri
    ).strip()

    if not coverage_raster_uri:
        raise ValueError(
            "coverage_raster_uri must not be empty."
        )

    authoritative_coverage_area_sq_m = (
        _validate_positive_finite(
            authoritative_coverage_area_sq_m,
            name="authoritative_coverage_area_sq_m",
        )
    )

    processing_time_seconds = (
        _validate_nonnegative_finite(
            processing_time_seconds,
            name="processing_time_seconds",
        )
    )

    document = _load_feature_collection(
        display_geojson_path
    )

    features = document[
        "features"
    ]

    feature_geometry_json = [
        json.dumps(
            feature[
                "geometry"
            ]
        )
        for feature in features
    ]

    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH input_geometries AS (
                SELECT
                    ST_SetSRID(
                        ST_GeomFromGeoJSON(value),
                        4326
                    ) AS geom

                FROM unnest(
                    %s::text[]
                ) AS value
            ),

            dissolved AS (
                SELECT
                    ST_Multi(
                        ST_CollectionExtract(
                            ST_UnaryUnion(
                                ST_Collect(
                                    geom
                                )
                            ),
                            3
                        )
                    ) AS geom

                FROM input_geometries
            )

            UPDATE coverage_runs

            SET
                status = 'completed',
                completed_at = NOW(),

                propagation_model = %s,
                propagation_model_version = %s,

                coverage_raster_uri = %s,

                coverage_geometry = (
                    SELECT geom
                    FROM dissolved
                ),

                coverage_area_sq_m = %s,

                processing_time_seconds = %s,

                error_message = NULL

            WHERE id = %s;
            """,
            (
                feature_geometry_json,
                RAPID_PROPAGATION_MODEL,
                RAPID_PROPAGATION_MODEL_VERSION,
                coverage_raster_uri,
                authoritative_coverage_area_sq_m,
                processing_time_seconds,
                run_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Rapid coverage run was not found or was not updated."
            )

    connection.commit()