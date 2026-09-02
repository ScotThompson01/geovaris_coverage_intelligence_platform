"""Load deterministic synthetic TEST-002 locations into PostGIS.

These points are NOT FCC Broadband Serviceable Location Fabric data.

They exist only to validate the GeoVaris Fabric-location analytics
pipeline:

synthetic points
    -> PostGIS
    -> coverage intersection
    -> saved coverage-run analytics
    -> API
    -> UI

The point grid is derived from the governed TEST-002 DEM extent so the
test dataset is reproducible.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
import rasterio
from pyproj import Transformer


DATASET_SOURCE = (
    "GeoVaris Synthetic Test Data"
)

FABRIC_VERSION = (
    "test002-demo-2026.1"
)

DATASET_VINTAGE = (
    "synthetic"
)

GRID_SPACING_M = 1000.0

EXPECTED_DEM_CRS = (
    "EPSG:32617"
)

DEM_PATH = Path(
    "rf-engine/data/dem/test002_60km_30m_utm17.tif"
)


def get_database_url() -> str:
    database_url = os.environ.get(
        "GEOVARIS_DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "GEOVARIS_DATABASE_URL is not configured."
        )

    return database_url


def build_points() -> list[
    tuple[
        str,
        float,
        float,
    ]
]:
    """Build deterministic 1 km grid points from the DEM extent."""

    dem_path = (
        DEM_PATH
        .expanduser()
        .resolve()
    )

    if not dem_path.is_file():
        raise FileNotFoundError(
            f"TEST-002 DEM not found: {dem_path}"
        )

    with rasterio.open(
        dem_path
    ) as dataset:
        if dataset.crs is None:
            raise ValueError(
                "TEST-002 DEM has no CRS."
            )

        dem_crs = (
            dataset.crs.to_string()
        )

        if dem_crs != EXPECTED_DEM_CRS:
            raise ValueError(
                "Unexpected TEST-002 DEM CRS. "
                f"Expected {EXPECTED_DEM_CRS}, "
                f"found {dem_crs}."
            )

        bounds = dataset.bounds

        width_m = (
            bounds.right
            - bounds.left
        )

        height_m = (
            bounds.top
            - bounds.bottom
        )

        columns = round(
            width_m
            / GRID_SPACING_M
        )

        rows = round(
            height_m
            / GRID_SPACING_M
        )

    if columns <= 0 or rows <= 0:
        raise ValueError(
            "DEM extent is too small for the configured grid."
        )

    transformer = Transformer.from_crs(
        EXPECTED_DEM_CRS,
        "EPSG:4326",
        always_xy=True,
    )

    points: list[
        tuple[
            str,
            float,
            float,
        ]
    ] = []

    location_number = 1

    for row_index in range(
        rows
    ):
        northing = (
            bounds.bottom
            + (
                row_index
                + 0.5
            )
            * GRID_SPACING_M
        )

        for column_index in range(
            columns
        ):
            easting = (
                bounds.left
                + (
                    column_index
                    + 0.5
                )
                * GRID_SPACING_M
            )

            longitude, latitude = (
                transformer.transform(
                    easting,
                    northing,
                )
            )

            location_id = (
                "TEST002-"
                f"{location_number:06d}"
            )

            points.append(
                (
                    location_id,
                    longitude,
                    latitude,
                )
            )

            location_number += 1

    print(
        "TEST-002 DEM extent:"
    )

    print(
        f"  Left:   {bounds.left:.3f} m"
    )

    print(
        f"  Bottom: {bounds.bottom:.3f} m"
    )

    print(
        f"  Right:  {bounds.right:.3f} m"
    )

    print(
        f"  Top:    {bounds.top:.3f} m"
    )

    print(
        "Synthetic grid:"
    )

    print(
        f"  Spacing: {GRID_SPACING_M:.0f} m"
    )

    print(
        f"  Columns: {columns}"
    )

    print(
        f"  Rows:    {rows}"
    )

    print(
        f"  Points:  {len(points):,}"
    )

    return points


def load_points(
    points: list[
        tuple[
            str,
            float,
            float,
        ]
    ],
) -> None:
    """Load synthetic locations using a transaction-local staging table."""

    database_url = (
        get_database_url()
    )

    with psycopg.connect(
        database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TEMP TABLE synthetic_fabric_load (
                    location_id TEXT NOT NULL,
                    longitude DOUBLE PRECISION NOT NULL,
                    latitude DOUBLE PRECISION NOT NULL
                )
                ON COMMIT DROP;
                """
            )

            with cursor.copy(
                """
                COPY synthetic_fabric_load (
                    location_id,
                    longitude,
                    latitude
                )
                FROM STDIN
                """
            ) as copy:
                for point in points:
                    copy.write_row(
                        point
                    )

            cursor.execute(
                """
                INSERT INTO fabric_locations (
                    location_id,
                    state_fips,
                    county_fips,
                    dataset_source,
                    fabric_version,
                    dataset_vintage,
                    geometry
                )

                SELECT
                    location_id,
                    NULL,
                    NULL,
                    %s,
                    %s,
                    %s,

                    ST_SetSRID(
                        ST_MakePoint(
                            longitude,
                            latitude
                        ),
                        4326
                    )

                FROM synthetic_fabric_load

                ON CONFLICT (
                    dataset_source,
                    fabric_version,
                    location_id
                )
                DO NOTHING;
                """,
                (
                    DATASET_SOURCE,
                    FABRIC_VERSION,
                    DATASET_VINTAGE,
                ),
            )

            inserted_rows = (
                cursor.rowcount
            )

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS location_count,

                    COUNT(*) FILTER (
                        WHERE NOT ST_IsValid(
                            geometry
                        )
                    ) AS invalid_geometry_count,

                    MIN(
                        ST_X(
                            geometry
                        )
                    ) AS minimum_longitude,

                    MAX(
                        ST_X(
                            geometry
                        )
                    ) AS maximum_longitude,

                    MIN(
                        ST_Y(
                            geometry
                        )
                    ) AS minimum_latitude,

                    MAX(
                        ST_Y(
                            geometry
                        )
                    ) AS maximum_latitude

                FROM fabric_locations

                WHERE dataset_source = %s
                  AND fabric_version = %s
                  AND dataset_vintage = %s;
                """,
                (
                    DATASET_SOURCE,
                    FABRIC_VERSION,
                    DATASET_VINTAGE,
                ),
            )

            result = (
                cursor.fetchone()
            )

        connection.commit()

    print()
    print(
        "Synthetic TEST-002 dataset loaded."
    )

    print(
        f"Inserted this run: {inserted_rows:,}"
    )

    print(
        f"Stored locations: {result[0]:,}"
    )

    print(
        f"Invalid geometries: {result[1]:,}"
    )

    print(
        "Longitude range: "
        f"{result[2]:.6f} "
        f"to {result[3]:.6f}"
    )

    print(
        "Latitude range: "
        f"{result[4]:.6f} "
        f"to {result[5]:.6f}"
    )

    print()
    print(
        "Dataset source: "
        f"{DATASET_SOURCE}"
    )

    print(
        "Fabric version: "
        f"{FABRIC_VERSION}"
    )

    print(
        "Dataset vintage: "
        f"{DATASET_VINTAGE}"
    )

    print()
    print(
        "IMPORTANT: These are synthetic test locations, "
        "not FCC Fabric records."
    )


def main() -> int:
    points = (
        build_points()
    )

    load_points(
        points
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
