"""Database completion helpers for GeoVaris Rapid Coverage runs.

This module stores completed Rapid Coverage Estimate results in the
existing coverage_runs table.

Important separation:

coverage_area_sq_m
    Authoritative analytical area derived from the Rapid raster.

coverage_geometry
    Display-oriented geometry derived from the filtered Rapid GeoJSON.

covered_population
    Estimated population derived from Census block population,
    area-weighted by intersection with coverage_geometry.

The display geometry may omit very small disconnected components.
Therefore coverage_area_sq_m must never be recalculated from
coverage_geometry for Rapid Coverage runs.

Population coverage is currently based on the display geometry and is
therefore an estimate rather than a raster-authoritative population
result.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

import psycopg


RAPID_PROPAGATION_MODEL = "rapid_coverage"
RAPID_PROPAGATION_MODEL_VERSION = "demo-2026.1"

POPULATION_DATASET_SOURCE = (
    "U.S. Census Bureau"
)

POPULATION_DATASET_VERSION = (
    "2020 TIGER/Line Census Tabulation Blocks "
    "with Population and Housing Counts"
)

POPULATION_DATASET_VINTAGE = 2020

POPULATION_ALLOCATION_METHOD = (
    "block_area_weighted"
)

POPULATION_GEOMETRY_BASIS = (
    "display_geometry"
)


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
    processing_started_at: float,
) -> None:
    """Store a completed Rapid Coverage result.

    Display features are dissolved in PostGIS.

    Population analytics are calculated in the same database statement
    using governed Census blocks and the display coverage polygons.

    The authoritative coverage area comes directly from raster analytics
    and is stored separately from the display geometry.

    The final processing time is calculated after PostGIS population
    analytics finish so processing_time_seconds reflects the complete
    end-to-end Rapid Coverage workflow.
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

    processing_started_at = (
        _validate_nonnegative_finite(
            processing_started_at,
            name="processing_started_at",
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

            coverage_parts AS (
                SELECT
                    (
                        ST_Dump(
                            geom
                        )
                    ).geom AS geom

                FROM input_geometries
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
            ),

            matching_pairs AS (
                SELECT
                    pb.geoid,
                    pb.population,

                    pb.geometry
                        AS block_geometry,

                    cp.geom
                        AS coverage_geometry

                FROM coverage_parts cp

                JOIN population_blocks pb
                    ON pb.dataset_source = %s
                    AND pb.dataset_version = %s
                    AND pb.dataset_vintage = %s
                    AND pb.geometry
                        && cp.geom
                    AND ST_Intersects(
                        pb.geometry,
                        cp.geom
                    )
            ),

            intersection_areas AS (
                SELECT
                    geoid,
                    population,

                    ST_Area(
                        block_geometry::geography
                    ) AS block_area_sq_m,

                    ST_Area(
                        ST_Intersection(
                            block_geometry,
                            coverage_geometry
                        )::geography
                    ) AS intersection_area_sq_m

                FROM matching_pairs
            ),

            block_totals AS (
                SELECT
                    geoid,

                    MAX(
                        population
                    ) AS population,

                    MAX(
                        block_area_sq_m
                    ) AS block_area_sq_m,

                    SUM(
                        intersection_area_sq_m
                    ) AS covered_area_sq_m

                FROM intersection_areas

                GROUP BY
                    geoid
            ),

            weighted_blocks AS (
                SELECT
                    geoid,
                    population,

                    CASE
                        WHEN block_area_sq_m <= 0
                            THEN 0.0

                        ELSE LEAST(
                            1.0,
                            GREATEST(
                                0.0,
                                covered_area_sq_m
                                /
                                block_area_sq_m
                            )
                        )
                    END AS coverage_fraction

                FROM block_totals
            ),

            population_summary AS (
                SELECT
                    COUNT(*) FILTER (
                        WHERE coverage_fraction > 0
                    )::integer
                        AS intersecting_blocks,

                    COUNT(*) FILTER (
                        WHERE coverage_fraction
                            >= 0.999999
                    )::integer
                        AS fully_covered_blocks,

                    COUNT(*) FILTER (
                        WHERE coverage_fraction > 0
                          AND coverage_fraction
                            < 0.999999
                    )::integer
                        AS partially_covered_blocks,

                    ROUND(
                        COALESCE(
                            SUM(
                                population
                                *
                                coverage_fraction
                            ),
                            0
                        )
                    )::bigint
                        AS covered_population

                FROM weighted_blocks
            )

            UPDATE coverage_runs AS cr

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

                covered_population = (
                    SELECT covered_population
                    FROM population_summary
                ),

                census_vintage = %s,

                population_dataset_source = %s,
                population_dataset_version = %s,
                population_allocation_method = %s,
                population_geometry_basis = %s,

                population_intersecting_blocks = (
                    SELECT intersecting_blocks
                    FROM population_summary
                ),

                population_fully_covered_blocks = (
                    SELECT fully_covered_blocks
                    FROM population_summary
                ),

                population_partially_covered_blocks = (
                    SELECT partially_covered_blocks
                    FROM population_summary
                ),

                population_calculated_at = NOW(),

                processing_time_seconds = NULL,

                error_message = NULL

            WHERE cr.id = %s

              AND (
                  SELECT intersecting_blocks
                  FROM population_summary
              ) > 0;
            """,
            (
                feature_geometry_json,

                POPULATION_DATASET_SOURCE,
                POPULATION_DATASET_VERSION,
                POPULATION_DATASET_VINTAGE,

                RAPID_PROPAGATION_MODEL,
                RAPID_PROPAGATION_MODEL_VERSION,

                coverage_raster_uri,
                authoritative_coverage_area_sq_m,

                str(
                    POPULATION_DATASET_VINTAGE
                ),

                POPULATION_DATASET_SOURCE,
                POPULATION_DATASET_VERSION,
                POPULATION_ALLOCATION_METHOD,
                POPULATION_GEOMETRY_BASIS,

                run_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Rapid coverage run was not updated. "
                "The run may not exist or governed population "
                "data may not overlap the coverage footprint."
            )

        total_processing_time_seconds = (
            time.perf_counter()
            - processing_started_at
        )

        total_processing_time_seconds = (
            _validate_nonnegative_finite(
                total_processing_time_seconds,
                name="total_processing_time_seconds",
            )
        )

        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                processing_time_seconds = %s
            WHERE id = %s;
            """,
            (
                total_processing_time_seconds,
                run_id,
            ),
        )

        if cursor.rowcount != 1:
            raise ValueError(
                "Rapid coverage processing time "
                "could not be updated."
            )

    connection.commit()