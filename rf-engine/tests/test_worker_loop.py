import unittest
from unittest.mock import patch

from geovaris_rf.worker_loop import (
    process_one_available_run,
    recover_stale_runs,
)


class WorkerLoopTests(unittest.TestCase):
    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_rapid_run"
    )
    def test_rapid_run_is_processed_first(
        self,
        mock_rapid,
        mock_itm,
        mock_free_space,
    ):
        mock_rapid.return_value = True

        processed = process_one_available_run()

        self.assertTrue(processed)

        mock_rapid.assert_called_once_with()
        mock_itm.assert_not_called()
        mock_free_space.assert_not_called()

    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_rapid_run"
    )
    def test_itm_runs_when_no_rapid_run_exists(
        self,
        mock_rapid,
        mock_itm,
        mock_free_space,
    ):
        mock_rapid.return_value = False
        mock_itm.return_value = True

        processed = process_one_available_run()

        self.assertTrue(processed)

        mock_rapid.assert_called_once_with()
        mock_itm.assert_called_once_with()
        mock_free_space.assert_not_called()

    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_rapid_run"
    )
    def test_free_space_runs_when_no_rapid_or_itm_run_exists(
        self,
        mock_rapid,
        mock_itm,
        mock_free_space,
    ):
        mock_rapid.return_value = False
        mock_itm.return_value = False
        mock_free_space.return_value = True

        processed = process_one_available_run()

        self.assertTrue(processed)

        mock_rapid.assert_called_once_with()
        mock_itm.assert_called_once_with()
        mock_free_space.assert_called_once_with()

    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_rapid_run"
    )
    def test_no_available_run_returns_false(
        self,
        mock_rapid,
        mock_itm,
        mock_free_space,
    ):
        mock_rapid.return_value = False
        mock_itm.return_value = False
        mock_free_space.return_value = False

        processed = process_one_available_run()

        self.assertFalse(processed)

        mock_rapid.assert_called_once_with()
        mock_itm.assert_called_once_with()
        mock_free_space.assert_called_once_with()


class WorkerLoopRecoveryTests(unittest.TestCase):
    @patch(
        "geovaris_rf.worker_loop.recover_stale_coverage_runs"
    )
    @patch(
        "geovaris_rf.worker_loop.get_database_url"
    )
    def test_recover_stale_runs_uses_database_url(
        self,
        mock_get_database_url,
        mock_recover,
    ):
        mock_get_database_url.return_value = (
            "postgresql://test"
        )

        mock_recover.return_value = []

        recover_stale_runs()

        mock_get_database_url.assert_called_once_with()

        mock_recover.assert_called_once_with(
            database_url="postgresql://test",
        )

    @patch(
        "builtins.print"
    )
    @patch(
        "geovaris_rf.worker_loop.recover_stale_coverage_runs"
    )
    @patch(
        "geovaris_rf.worker_loop.get_database_url"
    )
    def test_recovered_runs_are_logged(
        self,
        mock_get_database_url,
        mock_recover,
        mock_print,
    ):
        mock_get_database_url.return_value = (
            "postgresql://test"
        )

        mock_recover.return_value = [
            {
                "id": "run-123",
                "propagation_model": "rapid_coverage",
                "status": "pending",
            },
            {
                "id": "run-456",
                "propagation_model": "ntia_itm",
                "status": "failed",
            },
        ]

        recover_stale_runs()

        mock_print.assert_any_call(
            "Recovered stale coverage run "
            "run-123 "
            "(rapid_coverage) "
            "to status "
            "pending."
        )

        mock_print.assert_any_call(
            "Recovered stale coverage run "
            "run-456 "
            "(ntia_itm) "
            "to status "
            "failed."
        )


if __name__ == "__main__":
    unittest.main()
