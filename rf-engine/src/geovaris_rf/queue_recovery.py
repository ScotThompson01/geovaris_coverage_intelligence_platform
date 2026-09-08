"""Shared stale coverage-run recovery for GeoVaris workers.

A coverage run is eligible for recovery only when it remains in the
``processing`` state and its ``heartbeat_at`` timestamp is older than the
configured stale threshold.

Recovery is performed atomically in PostgreSQL:

- runs with remaining attempts return to ``pending`` after the normal
  retry delay;
- runs that exhausted ``max_attempts`` become terminally ``failed``;
- retryable runs release their claim/heartbeat metadata;
- terminal failures retain final claim metadata for traceability.

The periodic worker heartbeat must be enabled before stale recovery is
used in a continuously running worker.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row


DEFAULT_STALE_AFTER_SECONDS = 300
DEFAULT_RETRY_DELAY_SECONDS = 30

STALE_RECOVERY_ERROR_MESSAGE = (
    "Coverage run recovered after worker heartbeat timeout."
)


def recover_stale_coverage_runs(
    *,
    database_url: str,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    retry_delay_seconds: int = DEFAULT_RETRY_DELAY_SECONDS,
) -> list[dict[str, Any]]:
    """Recover stale processing coverage runs.

    Args:
        database_url:
            PostgreSQL connection string used only for this recovery sweep.
        stale_after_seconds:
            Minimum heartbeat age required before a processing run is stale.
        retry_delay_seconds:
            Delay before a retryable stale run becomes eligible to be claimed.

    Returns:
        One dictionary per recovered coverage run, containing the run ID,
        propagation model, resulting status, attempt counters, and retry time.

    Raises:
        ValueError:
            If either interval is not greater than zero.
    """

    if stale_after_seconds <= 0:
        raise ValueError(
            "stale_after_seconds must be greater than zero."
        )

    if retry_delay_seconds <= 0:
        raise ValueError(
            "retry_delay_seconds must be greater than zero."
        )

    with psycopg.connect(
        database_url
    ) as connection:
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

                WHERE status = 'processing'
                  AND heartbeat_at IS NOT NULL
                  AND heartbeat_at
                      < NOW()
                        - (
                            %s
                            * INTERVAL '1 second'
                        )

                RETURNING
                    id,
                    propagation_model,
                    status,
                    attempt_count,
                    max_attempts,
                    next_attempt_at;
                """,
                (
                    retry_delay_seconds,
                    STALE_RECOVERY_ERROR_MESSAGE,
                    stale_after_seconds,
                ),
            )

            recovered_rows = (
                cursor.fetchall()
            )

        connection.commit()

    return [
        dict(
            row
        )
        for row in recovered_rows
    ]
