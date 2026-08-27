import tempfile
import unittest
from pathlib import Path

from geovaris_rf.storage import (
    LocalCoverageStorage,
)


class LocalCoverageStorageTests(
    unittest.TestCase
):
    def test_publish_returns_stable_artifact_key(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = (
                Path(temp_dir)
                / "coverage.tif"
            )

            artifact.write_bytes(
                b"test"
            )

            storage = (
                LocalCoverageStorage()
            )

            result = storage.publish(
                local_path=artifact,
                artifact_key=(
                    "coverage-runs/"
                    "abc-123/"
                    "coverage.tif"
                ),
            )

            self.assertEqual(
                result,
                (
                    "coverage-runs/"
                    "abc-123/"
                    "coverage.tif"
                ),
            )

    def test_missing_local_artifact_is_rejected(
        self,
    ):
        storage = (
            LocalCoverageStorage()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            missing = (
                Path(temp_dir)
                / "missing.tif"
            )

            with self.assertRaises(
                FileNotFoundError
            ):
                storage.publish(
                    local_path=missing,
                    artifact_key=(
                        "coverage-runs/"
                        "abc-123/"
                        "coverage.tif"
                    ),
                )

    def test_directory_is_rejected(
        self,
    ):
        storage = (
            LocalCoverageStorage()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(
                ValueError
            ):
                storage.publish(
                    local_path=Path(
                        temp_dir
                    ),
                    artifact_key=(
                        "coverage-runs/"
                        "abc-123/"
                        "coverage.tif"
                    ),
                )

    def test_empty_artifact_key_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = (
                Path(temp_dir)
                / "coverage.tif"
            )

            artifact.write_bytes(
                b"test"
            )

            storage = (
                LocalCoverageStorage()
            )

            with self.assertRaises(
                ValueError
            ):
                storage.publish(
                    local_path=artifact,
                    artifact_key="   ",
                )

    def test_windows_separator_in_key_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = (
                Path(temp_dir)
                / "coverage.tif"
            )

            artifact.write_bytes(
                b"test"
            )

            storage = (
                LocalCoverageStorage()
            )

            with self.assertRaises(
                ValueError
            ):
                storage.publish(
                    local_path=artifact,
                    artifact_key=(
                        "coverage-runs\\"
                        "abc-123\\"
                        "coverage.tif"
                    ),
                )


if __name__ == "__main__":
    unittest.main()