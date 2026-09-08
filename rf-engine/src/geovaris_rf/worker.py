"""GeoVaris RF development worker.

Processes one pending coverage run using the free_space_test model.

This worker is an MVP development implementation. It is not yet a
production job-queue system.
"""

from __future__ import annotations

import os
import socket
import sys
import time
from typing import Any

import psycopg
from psycopg.rows import dict_row

from geovaris_rf.free_space import estimated_coverage_radius_m
from geovaris_rf.queue_heartbeat import (
    CoverageRunHeartbeat,
)


RUN_ID_ENVIRONMENT_VARIABLE = (
    "GEOVARIS_COVERAGE_RUN_ID"
)

RETRY_DELAY_SECONDS = 30


def get_database_url() -> str:
    """Read the Neon PostgreSQL connection string."""

    database_url = os.getenv("GEOVARIS_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "GEOVARIS_DATABASE_URL environment variable is not configured."
        )

    return database_url


def get_requested_run_id() -> str | None:
    """Return an optional explicitly requested coverage run ID."""

    value = os.getenv(
        RUN_ID_ENVIRONMENT_VARIABLE
    )

    if value is None:
        return None

    value = value.strip()

    return value or None


def get_worker_id() -> str:
    """Return the identifier recorded when this worker claims work.

    GEOVARIS_WORKER_ID may be configured explicitly in deployed
    environments. Development workers fall back to hostname + PID.
    """

    configured_worker_id = (
        os.getenv(
            "GEOVARIS_WORKER_ID",
            "",
        ).strip()
    )

    if configured_worker_id:
        return configured_worker_id

    return (
        f"{socket.gethostname()}:{os.getpid()}"
    )


def claim_pending_run(
    connection: psycopg.Connection,
) -> dict[str, Any] | None:
    """Claim one eligible pending free-space coverage run.

    When GEOVARIS_COVERAGE_RUN_ID is configured, only that pending
    free-space run is eligible. Otherwise the oldest eligible
    pending free-space run is claimed.

    The database row is locked while the claim metadata and status
    transition are written so concurrent workers cannot claim the
    same coverage run.
    """

    requested_run_id = (
        get_requested_run_id()
    )

    worker_id = (
        get_worker_id()
    )

    with connection.transaction():
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            if requested_run_id is None:
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
                      AND attempt_count < max_attempts
                      AND (
                          next_attempt_at IS NULL
                          OR next_attempt_at <= NOW()
                      )
                    ORDER BY created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1;
                    """
                )
            else:
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
                    WHERE id = %s
                      AND status = 'pending'
                      AND propagation_model = 'free_space_test'
                      AND attempt_count < max_attempts
                      AND (
                          next_attempt_at IS NULL
                          OR next_attempt_at <= NOW()
                      )
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1;
                    """,
                    (
                        requested_run_id,
                    ),
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
                    error_message = NULL,
                    attempt_count =
                        attempt_count + 1,
                    claimed_at = NOW(),
                    claimed_by = %s,
                    heartbeat_at = NOW(),
                    next_attempt_at = NULL
                WHERE id = %s;
                """,
                (
                    worker_id,
                    coverage_run[
                        "id"
                    ],
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Free-space coverage run could not be marked processing."
                )

            return coverage_run


def refresh_heartbeat(
    connection: psycopg.Connection,
    *,
    run_id: Any,
) -> None:
    """Refresh the heartbeat for one actively processing free-space run.

    The update is limited to rows that remain in the processing state
    so a late heartbeat cannot modify a completed, failed, or retried run.
    """

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                heartbeat_at = NOW()
            WHERE id = %s
              AND status = 'processing';
            """,
            (
                run_id,
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "Free-space coverage run heartbeat could not be refreshed."
            )

    connection.commit()



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
) -> dict[str, Any]:
    """Schedule a retry or mark a run terminally failed.

    Runs with remaining attempts return to pending after a fixed
    retry delay. Runs that have exhausted max_attempts become failed.
    """

    with connection.cursor(
        row_factory=dict_row
    ) as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                status =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN 'pending'
                        ELSE 'failed'
                    END,

                completed_at =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN NULL
                        ELSE NOW()
                    END,

                next_attempt_at =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN NOW()
                                + (
                                    %s
                                    * INTERVAL '1 second'
                                )
                        ELSE NULL
                    END,

                started_at =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN NULL
                        ELSE started_at
                    END,

                claimed_at =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN NULL
                        ELSE claimed_at
                    END,

                claimed_by =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN NULL
                        ELSE claimed_by
                    END,

                heartbeat_at =
                    CASE
                        WHEN attempt_count < max_attempts
                            THEN NULL
                        ELSE heartbeat_at
                    END,

                last_error_at = NOW(),
                error_message = %s

            WHERE id = %s

            RETURNING
                status,
                attempt_count,
                max_attempts,
                next_attempt_at;
            """,
            (
                RETRY_DELAY_SECONDS,
                error_message[
                    :2000
                ],
                run_id,
            ),
        )

        result = cursor.fetchone()

        if result is None:
            raise RuntimeError(
                "Coverage run failure state could not be updated."
            )

    connection.commit()

    return dict(
        result
    )


def process_one_run() -> bool:
    """Claim and process one pending development coverage run."""

    database_url = get_database_url()

    requested_run_id = (
        get_requested_run_id()
    )

    if requested_run_id is not None:
        print(
            "Requested coverage run: "
            f"{requested_run_id}"
        )

    with psycopg.connect(database_url) as connection:
        coverage_run = claim_pending_run(connection)

        if coverage_run is None:
            if requested_run_id is None:
                print(
                    "No pending free_space_test coverage runs found."
                )
            else:
                print(
                    "Requested coverage run was not found, "
                    "is not pending, or is not a free_space_test run: "
                    f"{requested_run_id}"
                )

            return False

        run_id = coverage_run["id"]

        print(f"Processing coverage run {run_id}")

        started = time.perf_counter()

        try:
            with CoverageRunHeartbeat(
                database_url=database_url,
                run_id=run_id,
            ):
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

                refresh_heartbeat(
                    connection,
                    run_id=run_id,
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
            failure_result = fail_run(
                connection=connection,
                run_id=run_id,
                error_message=str(exc),
            )

            if (
                failure_result[
                    "status"
                ]
                == "pending"
            ):
                print(
                    f"Coverage run {run_id} attempt "
                    f"{failure_result['attempt_count']} failed: {exc}",
                    file=sys.stderr,
                )

                print(
                    "Retry scheduled for "
                    f"{failure_result['next_attempt_at']}."
                )
            else:
                print(
                    f"Coverage run {run_id} failed after "
                    f"{failure_result['attempt_count']} attempts: {exc}",
                    file=sys.stderr,
                )

            return True


if __name__ == "__main__":
    process_one_run()
