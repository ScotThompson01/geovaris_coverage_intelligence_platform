import unittest
from unittest.mock import MagicMock, patch

from geovaris_rf.queue_recovery import (
    STALE_RECOVERY_ERROR_MESSAGE,
    recover_stale_coverage_runs,
)


class QueueRecoveryTests(
    unittest.TestCase
):
    def _mock_database(
        self,
        *,
        rows: list[dict],
    ) -> tuple[
        MagicMock,
        MagicMock,
    ]:
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = (
            connection
        )

        connection.cursor.return_value.__enter__.return_value = (
            cursor
        )

        cursor.fetchall.return_value = rows

        return (
            connection,
            cursor,
        )

    def test_recovery_uses_stale_processing_contract(
        self,
    ) -> None:
        connection, cursor = (
            self._mock_database(
                rows=[
                    {
                        "id": "run-123",
                        "propagation_model": (
                            "rapid_coverage"
                        ),
                        "status": "pending",
                        "attempt_count": 1,
                        "max_attempts": 3,
                        "next_attempt_at": (
                            "retry-time"
                        ),
                    }
                ]
            )
        )

        with patch(
            "geovaris_rf.queue_recovery.psycopg.connect",
            return_value=connection,
        ) as mock_connect:
            recovered = (
                recover_stale_coverage_runs(
                    database_url=(
                        "postgresql://test"
                    ),
                    stale_after_seconds=300,
                    retry_delay_seconds=30,
                )
            )

        mock_connect.assert_called_once_with(
            "postgresql://test"
        )

        cursor.execute.assert_called_once()

        sql_text = (
            cursor.execute.call_args[
                0
            ][
                0
            ]
        )

        params = (
            cursor.execute.call_args[
                0
            ][
                1
            ]
        )

        self.assertIn(
            "WHERE status = 'processing'",
            sql_text,
        )

        self.assertIn(
            "heartbeat_at IS NOT NULL",
            sql_text,
        )

        self.assertIn(
            "WHEN attempt_count < max_attempts",
            sql_text,
        )

        self.assertIn(
            "THEN 'pending'",
            sql_text,
        )

        self.assertIn(
            "ELSE 'failed'",
            sql_text,
        )

        self.assertIn(
            "next_attempt_at",
            sql_text,
        )

        self.assertIn(
            "claimed_by",
            sql_text,
        )

        self.assertIn(
            "heartbeat_at",
            sql_text,
        )

        self.assertIn(
            "last_error_at = NOW()",
            sql_text,
        )

        self.assertEqual(
            params,
            (
                30,
                STALE_RECOVERY_ERROR_MESSAGE,
                300,
            ),
        )

        self.assertEqual(
            recovered,
            [
                {
                    "id": "run-123",
                    "propagation_model": (
                        "rapid_coverage"
                    ),
                    "status": "pending",
                    "attempt_count": 1,
                    "max_attempts": 3,
                    "next_attempt_at": (
                        "retry-time"
                    ),
                }
            ],
        )

        connection.commit.assert_called_once()

    def test_recovery_returns_empty_list_when_nothing_is_stale(
        self,
    ) -> None:
        connection, cursor = (
            self._mock_database(
                rows=[]
            )
        )

        with patch(
            "geovaris_rf.queue_recovery.psycopg.connect",
            return_value=connection,
        ):
            recovered = (
                recover_stale_coverage_runs(
                    database_url=(
                        "postgresql://test"
                    )
                )
            )

        self.assertEqual(
            recovered,
            [],
        )

        cursor.fetchall.assert_called_once()

        connection.commit.assert_called_once()

    def test_invalid_stale_threshold_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "stale_after_seconds",
        ):
            recover_stale_coverage_runs(
                database_url=(
                    "postgresql://test"
                ),
                stale_after_seconds=0,
            )

    def test_invalid_retry_delay_is_rejected(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "retry_delay_seconds",
        ):
            recover_stale_coverage_runs(
                database_url=(
                    "postgresql://test"
                ),
                retry_delay_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()
