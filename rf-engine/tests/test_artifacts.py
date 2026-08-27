import unittest
from pathlib import Path

from geovaris_rf.artifacts import (
    build_coverage_artifact_paths,
)


class CoverageArtifactPathTests(
    unittest.TestCase
):
    def test_builds_stable_raster_key(
        self,
    ):
        artifacts = (
            build_coverage_artifact_paths(
                output_root=Path(
                    "local-output"
                ),
                run_id="abc-123",
            )
        )

        self.assertEqual(
            artifacts.raster_key,
            "coverage-runs/abc-123/coverage.tif",
        )

    def test_builds_stable_geojson_key(
        self,
    ):
        artifacts = (
            build_coverage_artifact_paths(
                output_root=Path(
                    "local-output"
                ),
                run_id="abc-123",
            )
        )

        self.assertEqual(
            artifacts.geojson_key,
            "coverage-runs/abc-123/coverage.geojson",
        )

    def test_local_paths_are_separate_from_keys(
        self,
    ):
        output_root = Path(
            "local-output"
        )

        artifacts = (
            build_coverage_artifact_paths(
                output_root=output_root,
                run_id="abc-123",
            )
        )

        self.assertEqual(
            artifacts.raster_path,
            output_root
            / "abc-123"
            / "coverage.tif",
        )

        self.assertEqual(
            artifacts.geojson_path,
            output_root
            / "abc-123"
            / "coverage.geojson",
        )

    def test_empty_run_id_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            build_coverage_artifact_paths(
                output_root=Path(
                    "local-output"
                ),
                run_id="   ",
            )


if __name__ == "__main__":
    unittest.main()