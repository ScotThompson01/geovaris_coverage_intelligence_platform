"""Shared heartbeat support for GeoVaris coverage-run workers.

Coverage runs remain in ``processing`` while RF/GIS work is active.
This module periodically refreshes ``coverage_runs.heartbeat_at`` using
a database connection that is separate from the model worker's normal
processing connection.

Heartbeat failures are recorded and logged, but they do not terminate
the RF calculation. Stale-run recovery must use a threshold comfortably
larger than the heartbeat interval.
"""

from __future__ import annotations

import sys
import threading
from typing import Any

import psycopg


HEARTBEAT_INTERVAL_SECONDS = 30.0

HEARTBEAT_THREAD_JOIN_TIMEOUT_SECONDS = 5.0


class CoverageRunHeartbeat:
    """Maintain a periodic heartbeat for one processing coverage run."""

    def __init__(
        self,
        *,
        database_url: str,
        run_id: Any,
        interval_seconds: float = HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError(
                "Heartbeat interval must be greater than zero."
            )

        self.database_url = database_url
        self.run_id = run_id
        self.interval_seconds = float(
            interval_seconds
        )

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error: str | None = None

    def __enter__(
        self,
    ) -> "CoverageRunHeartbeat":
        self.start()

        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.stop()

    def start(
        self,
    ) -> None:
        """Start periodic heartbeat refreshes.

        An immediate refresh is attempted first so the run has a fresh
        heartbeat before entering a potentially long RF/GIS operation.
        The refresh uses its own database connection.
        """

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            raise RuntimeError(
                "Coverage run heartbeat is already running."
            )

        self._stop_event.clear()

        initial_result = (
            self._try_refresh_once()
        )

        if initial_result is False:
            return

        self._thread = threading.Thread(
            target=self._run,
            name=(
                "geovaris-coverage-heartbeat-"
                f"{self.run_id}"
            ),
            daemon=True,
        )

        self._thread.start()

    def stop(
        self,
    ) -> None:
        """Request heartbeat shutdown and wait briefly for the thread."""

        self._stop_event.set()

        thread = self._thread

        if (
            thread is not None
            and thread.is_alive()
        ):
            thread.join(
                timeout=(
                    HEARTBEAT_THREAD_JOIN_TIMEOUT_SECONDS
                )
            )

        self._thread = None

    def _run(
        self,
    ) -> None:
        """Refresh until stopped or the run leaves processing."""

        while not self._stop_event.wait(
            self.interval_seconds
        ):
            refresh_result = (
                self._try_refresh_once()
            )

            if refresh_result is False:
                return

    def _try_refresh_once(
        self,
    ) -> bool | None:
        """Attempt one refresh without propagating database failures.

        Returns:
            True when one processing row was refreshed.
            False when the run is no longer in processing.
            None when a database error occurred and the next periodic
            heartbeat should still be attempted.
        """

        try:
            refreshed = (
                self._refresh_once()
            )
        except Exception as exc:
            self.last_error = str(
                exc
            )

            print(
                "Coverage run heartbeat refresh failed "
                f"for {self.run_id}: {exc}",
                file=sys.stderr,
            )

            return None

        self.last_error = None

        if not refreshed:
            print(
                "Coverage run heartbeat stopped because "
                f"{self.run_id} is no longer processing.",
                file=sys.stderr,
            )

        return refreshed

    def _refresh_once(
        self,
    ) -> bool:
        """Refresh one processing run using a dedicated connection."""

        with psycopg.connect(
            self.database_url
        ) as connection:
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
                        self.run_id,
                    ),
                )

                refreshed = (
                    cursor.rowcount == 1
                )

            connection.commit()

        return refreshed
