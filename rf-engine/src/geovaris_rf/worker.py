"""GeoVaris RF development worker.

Processes one pending coverage run using the free_space_test model.

This worker is an MVP development implementation. It is not yet a
production job-queue system.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import psycopg
from psycopg.rows import dict_row

from geovaris_rf.free_space import estimated_coverage_radius_m


def get_database_url() -> str:
    """Read the Neon PostgreSQL connection string."""

    database_url = os.getenv("GEOVARIS_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "GEOVARIS_DATABASE_URL environment variable is not configured."
        )

    return database_url


def claim_pending_run(
    connection: psycopg.Connection,
) -> dict[str, Any] | None:
    """Claim the oldest pending free-space coverage run."""

    with connection.transaction():
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    customer_id,
                    scenario_id,
                    site_latitude,
                    site_longitude,
                    frequency_mhz,
                    eirp_watts,
                    receiver_threshold_dbm,
                    calculation_radius_m,
                    propagation_model
                FROM coverage_runs
                WHERE status = 'pending'
                  AND propagation_model = 'free_space_test'
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1;
                """
            )

            coverage_run = cursor.fetchone()

            if coverage_run is None:
                return None

            cursor.execute(
                """
                UPDATE coverage_runs
                SET
                    status = 'processing',
                    started_at = NOW(),
                    error_message = NULL
                WHERE id = %s;
                """,
                (coverage_run["id"],),
            )

            return coverage_run


def complete_run(
    connection: psycopg.Connection,
    coverage_run: dict[str, Any],
    estimated_radius_m: float,
    processing_time_seconds: float,
) -> None:
    """Store the free-space development result."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                status = 'completed',
                completed_at = NOW(),
                estimated_coverage_radius_m = %s,

                coverage_geometry =
                    ST_Multi(
                        ST_Buffer(
                            ST_SetSRID(
                                ST_MakePoint(
                                    site_longitude,
                                    site_latitude
                                ),
                                4326
                            )::geography,
                            %s
                        )::geometry
                    ),

                coverage_area_sq_m =
                    ST_Area(
                        ST_Buffer(
                            ST_SetSRID(
                                ST_MakePoint(
                                    site_longitude,
                                    site_latitude
                                ),
                                4326
                            )::geography,
                            %s
                        )
                    ),

                processing_time_seconds = %s,
                error_message = NULL

            WHERE id = %s;
            """,
            (
                estimated_radius_m,
                estimated_radius_m,
                estimated_radius_m,
                processing_time_seconds,
                coverage_run["id"],
            ),
        )

    connection.commit()


def fail_run(
    connection: psycopg.Connection,
    run_id: Any,
    error_message: str,
) -> None:
    """Mark a run failed while preserving the failure reason."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                status = 'failed',
                completed_at = NOW(),
                error_message = %s
            WHERE id = %s;
            """,
            (
                error_message[:2000],
                run_id,
            ),
        )

    connection.commit()


def process_one_run() -> bool:
    """Claim and process one pending development coverage run."""

    database_url = get_database_url()

    with psycopg.connect(database_url) as connection:
        coverage_run = claim_pending_run(connection)

        if coverage_run is None:
            print("No pending free_space_test coverage runs found.")
            return False

        run_id = coverage_run["id"]

        print(f"Processing coverage run {run_id}")

        started = time.perf_counter()

        try:
            estimated_radius_m = estimated_coverage_radius_m(
                frequency_mhz=float(
                    coverage_run["frequency_mhz"]
                ),
                eirp_watts=float(
                    coverage_run["eirp_watts"]
                ),
                receiver_threshold_dbm=float(
                    coverage_run["receiver_threshold_dbm"]
                ),
                calculation_radius_m=float(
                    coverage_run["calculation_radius_m"]
                ),
            )

            processing_time_seconds = (
                time.perf_counter() - started
            )

            complete_run(
                connection=connection,
                coverage_run=coverage_run,
                estimated_radius_m=estimated_radius_m,
                processing_time_seconds=processing_time_seconds,
            )

            print(
                f"Completed run {run_id}: "
                f"{estimated_radius_m:.2f} m radius"
            )

            return True

        except Exception as exc:
            fail_run(
                connection=connection,
                run_id=run_id,
                error_message=str(exc),
            )

            print(
                f"Coverage run {run_id} failed: {exc}",
                file=sys.stderr,
            )

            raise


if __name__ == "__main__":
    process_one_run()