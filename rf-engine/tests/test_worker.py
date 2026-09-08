import unittest
from unittest.mock import MagicMock

from geovaris_rf.worker import (
    fail_run,
    refresh_heartbeat,
)


class FreeSpaceWorkerHeartbeatTests(
    unittest.TestCase
):
    def test_refresh_heartbeat_updates_processing_run(
        self,
    ) -> None:
        connection = MagicMock()
        cursor = MagicMock()

        connection.cursor.return_value.__enter__.return_value = (
            cursor
        )

        cursor.rowcount = 1

        refresh_heartbeat(
            connection,
            run_id="run-123",
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
            "heartbeat_at = NOW()",
            sql_text,
        )

        self.assertIn(
            "status = 'processing'",
            sql_text,
        )

        self.assertEqual(
            params,
            (
                "run-123",
            ),
        )

        connection.commit.assert_called_once()


class FreeSpaceWorkerRetryTests(
    unittest.TestCase
):
    def test_fail_run_schedules_retry(
        self,
    ) -> None:
        connection = MagicMock()
        cursor = MagicMock()

        connection.cursor.return_value.__enter__.return_value = (
            cursor
        )

        cursor.fetchone.return_value = {
            "status": "pending",
            "attempt_count": 1,
            "max_attempts": 3,
            "next_attempt_at": "retry-time",
        }

        result = fail_run(
            connection,
            run_id="run-123",
            error_message="test failure",
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
            "last_error_at = NOW()",
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

        self.assertEqual(
            params[
                0
            ],
            30,
        )

        self.assertEqual(
            params[
                1
            ],
            "test failure",
        )

        self.assertEqual(
            params[
                2
            ],
            "run-123",
        )

        self.assertEqual(
            result[
                "status"
            ],
            "pending",
        )

        self.assertEqual(
            result[
                "attempt_count"
            ],
            1,
        )

        connection.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
