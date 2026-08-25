"""Site ground-elevation persistence for GeoVaris Coverage Intelligence.

Looks up an existing site's coordinates, retrieves governed USGS 3DEP
ground elevation, and stores the elevation plus DEM lineage on that site.

This is an MVP integration step. Automatic elevation lookup during site
creation will be added only after this workflow is validated.
"""

from __future__ import annotations

import os
import sys
from uuid import UUID

import psycopg

from geovaris_rf.dem import get_usgs_ground_elevation


DATABASE_ENV_VAR = "GEOVARIS_DATABASE_URL"


def get_database_url() -> str:
    """Return the configured GeoVaris database connection string."""

    database_url = os.environ.get(DATABASE_ENV_VAR)

    if not database_url:
        raise RuntimeError(
            f"{DATABASE_ENV_VAR} is not configured."
        )

    return database_url


def update_site_ground_elevation(site_id: str) -> None:
    """Retrieve and persist DEM-backed ground elevation for one site."""

    try:
        parsed_site_id = UUID(site_id)
    except ValueError as exc:
        raise ValueError(
            f"Invalid site UUID: {site_id}"
        ) from exc

    database_url = get_database_url()

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    latitude,
                    longitude
                FROM sites
                WHERE id = %s
                """,
                (parsed_site_id,),
            )

            site = cursor.fetchone()

            if site is None:
                raise RuntimeError(
                    f"Site not found: {site_id}"
                )

            _, site_name, latitude, longitude = site

            print(
                f"Looking up ground elevation for "
                f"{site_name} ({latitude}, {longitude})..."
            )

            elevation = get_usgs_ground_elevation(
                latitude=float(latitude),
                longitude=float(longitude),
            )

            cursor.execute(
                """
                UPDATE sites
                SET
                    ground_elevation_m = %s,
                    ground_elevation_source = %s,
                    ground_elevation_version = %s,
                    ground_elevation_horizontal_crs = %s,
                    ground_elevation_vertical_datum = %s,
                    ground_elevation_units = %s,
                    ground_elevation_resolution_m = %s,
                    ground_elevation_updated_at = NOW()
                WHERE id = %s
                """,
                (
                    elevation.elevation_m,
                    elevation.metadata.source,
                    elevation.metadata.version,
                    elevation.metadata.horizontal_crs,
                    elevation.metadata.vertical_datum,
                    elevation.metadata.units,
                    elevation.metadata.resolution_m,
                    parsed_site_id,
                ),
            )

        connection.commit()

    print(
        f"Updated {site_name}: "
        f"{elevation.elevation_m:.3f} m "
        f"({elevation.metadata.vertical_datum})"
    )


def main() -> None:
    """CLI entry point."""

    if len(sys.argv) != 2:
        print(
            "Usage: python -m geovaris_rf.site_elevation <site_uuid>"
        )
        raise SystemExit(1)

    update_site_ground_elevation(sys.argv[1])


if __name__ == "__main__":
    main()