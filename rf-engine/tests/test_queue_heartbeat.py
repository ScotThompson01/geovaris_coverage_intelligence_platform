import unittest
from unittest.mock import MagicMock, patch

from geovaris_rf.queue_heartbeat import (
    CoverageRunHeartbeat,
)


class CoverageRunHeartbeatTests(
    unittest.TestCase
):
    def test_refresh_once_updates_processing_run(
        self,
    ) -> None:
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = (
            connection
        )

        connection.cursor.return_value.__enter__.return_value = (
            cursor
        )

        cursor.rowcount = 1

        with patch(
            "geovaris_rf.queue_heartbeat.psycopg.connect",
            return_value=connection,
        ) as mock_connect:
            heartbeat = CoverageRunHeartbeat(
                database_url=(
                    "postgresql://test"
                ),
                run_id="run-123",
            )

            refreshed = (
                heartbeat._refresh_once()
            )

        self.assertTrue(
            refreshed
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

    def test_refresh_once_returns_false_when_run_is_not_processing(
        self,
    ) -> None:
        connection = MagicMock()
        cursor = MagicMock()

        connection.__enter__.return_value = (
            connection
        )

        connection.cursor.return_value.__enter__.return_value = (
            cursor
        )

        cursor.rowcount = 0

        with patch(
            "geovaris_rf.queue_heartbeat.psycopg.connect",
            return_value=connection,
        ):
            heartbeat = CoverageRunHeartbeat(
                database_url=(
                    "postgresql://test"
                ),
                run_id="run-123",
            )

            refreshed = (
                heartbeat._refresh_once()
            )

        self.assertFalse(
            refreshed
        )

        connection.commit.assert_called_once()

    def test_database_failure_is_recorded_without_raising(
        self,
    ) -> None:
        heartbeat = CoverageRunHeartbeat(
            database_url=(
                "postgresql://test"
            ),
            run_id="run-123",
        )

        with patch.object(
            heartbeat,
            "_refresh_once",
            side_effect=RuntimeError(
                "database unavailable"
            ),
        ):
            result = (
                heartbeat._try_refresh_once()
            )

        self.assertIsNone(
            result
        )

        self.assertEqual(
            heartbeat.last_error,
            "database unavailable",
        )

    def test_start_and_stop_manage_background_thread(
        self,
    ) -> None:
        heartbeat = CoverageRunHeartbeat(
            database_url=(
                "postgresql://test"
            ),
            run_id="run-123",
        )

        thread = MagicMock()

        thread.is_alive.return_value = True

        with (
            patch.object(
                heartbeat,
                "_try_refresh_once",
                return_value=True,
            ) as mock_refresh,
            patch(
                "geovaris_rf.queue_heartbeat.threading.Thread",
                return_value=thread,
            ) as mock_thread_class,
        ):
            heartbeat.start()

            mock_refresh.assert_called_once()

            mock_thread_class.assert_called_once()

            thread.start.assert_called_once()

            heartbeat.stop()

        thread.join.assert_called_once()


if __name__ == "__main__":
    unittest.main()
