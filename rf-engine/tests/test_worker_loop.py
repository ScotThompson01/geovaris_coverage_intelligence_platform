import unittest
from unittest.mock import patch

from geovaris_rf.worker_loop import (
    process_one_available_run,
)


class WorkerLoopTests(unittest.TestCase):
    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    def test_itm_run_is_processed_first(
        self,
        mock_itm,
        mock_free_space,
    ):
        mock_itm.return_value = True

        processed = process_one_available_run()

        self.assertTrue(processed)
        mock_itm.assert_called_once_with()
        mock_free_space.assert_not_called()

    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    def test_free_space_runs_when_no_itm_run_exists(
        self,
        mock_itm,
        mock_free_space,
    ):
        mock_itm.return_value = False
        mock_free_space.return_value = True

        processed = process_one_available_run()

        self.assertTrue(processed)
        mock_itm.assert_called_once_with()
        mock_free_space.assert_called_once_with()

    @patch(
        "geovaris_rf.worker_loop.process_one_run"
    )
    @patch(
        "geovaris_rf.worker_loop.process_one_itm_run"
    )
    def test_no_available_run_returns_false(
        self,
        mock_itm,
        mock_free_space,
    ):
        mock_itm.return_value = False
        mock_free_space.return_value = False

        processed = process_one_available_run()

        self.assertFalse(processed)
        mock_itm.assert_called_once_with()
        mock_free_space.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()