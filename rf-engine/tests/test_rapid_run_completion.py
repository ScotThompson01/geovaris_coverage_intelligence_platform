import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from geovaris_rf.rapid_run_completion import (
    RAPID_PROPAGATION_MODEL,
    RAPID_PROPAGATION_MODEL_VERSION,
    _load_feature_collection,
    complete_rapid_run,
)


class RapidRunCompletionTests(
    unittest.TestCase
):
    def _write_geojson(
        self,
        path: Path,
    ) -> None:
        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-81.0, 28.0],
                                [-80.9, 28.0],
                                [-80.9, 28.1],
                                [-81.0, 28.1],
                                [-81.0, 28.0],
                            ]
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-80.8, 28.0],
                                [-80.7, 28.0],
                                [-80.7, 28.1],
                                [-80.8, 28.1],
                                [-80.8, 28.0],
                            ]
                        ],
                    },
                },
            ],
        }

        path.write_text(
            json.dumps(
                document
            ),
            encoding="utf-8",
        )

    def test_load_feature_collection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(
                    temp_dir
                )
                / "display.geojson"
            )

            self._write_geojson(
                path
            )

            document = (
                _load_feature_collection(
                    path
                )
            )

            self.assertEqual(
                document[
                    "type"
                ],
                "FeatureCollection",
            )

            self.assertEqual(
                len(
                    document[
                        "features"
                    ]
                ),
                2,
            )

    def test_missing_geojson_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            FileNotFoundError
        ):
            _load_feature_collection(
                "missing.geojson"
            )

    def test_invalid_geometry_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(
                    temp_dir
                )
                / "display.geojson"
            )

            document = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                -81.0,
                                28.0,
                            ],
                        },
                    }
                ],
            }

            path.write_text(
                json.dumps(
                    document
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "unsupported geometry",
            ):
                _load_feature_collection(
                    path
                )

    def test_complete_run_updates_expected_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(
                    temp_dir
                )
                / "display.geojson"
            )

            self._write_geojson(
                path
            )

            connection = MagicMock()
            cursor = MagicMock()

            connection.cursor.return_value.__enter__.return_value = (
                cursor
            )

            cursor.rowcount = 1

            complete_rapid_run(
                connection,
                run_id="run-123",
                coverage_raster_uri=(
                    "coverage-runs/run-123/coverage.tif"
                ),
                display_geojson_path=path,
                authoritative_coverage_area_sq_m=(
                    550_094_400.0
                ),
                processing_time_seconds=6.25,
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
                "ST_UnaryUnion",
                sql_text,
            )

            self.assertIn(
                "coverage_area_sq_m = %s",
                sql_text,
            )

            self.assertEqual(
                params[
                    1
                ],
                RAPID_PROPAGATION_MODEL,
            )

            self.assertEqual(
                params[
                    2
                ],
                RAPID_PROPAGATION_MODEL_VERSION,
            )

            self.assertEqual(
                params[
                    4
                ],
                550_094_400.0,
            )

            connection.commit.assert_called_once()

    def test_zero_authoritative_area_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(
                    temp_dir
                )
                / "display.geojson"
            )

            self._write_geojson(
                path
            )

            with self.assertRaises(
                ValueError
            ):
                complete_rapid_run(
                    MagicMock(),
                    run_id="run-123",
                    coverage_raster_uri=(
                        "coverage-runs/run-123/coverage.tif"
                    ),
                    display_geojson_path=path,
                    authoritative_coverage_area_sq_m=0.0,
                    processing_time_seconds=1.0,
                )

    def test_missing_run_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(
                    temp_dir
                )
                / "display.geojson"
            )

            self._write_geojson(
                path
            )

            connection = MagicMock()
            cursor = MagicMock()

            connection.cursor.return_value.__enter__.return_value = (
                cursor
            )

            cursor.rowcount = 0

            with self.assertRaisesRegex(
                ValueError,
                "not found",
            ):
                complete_rapid_run(
                    connection,
                    run_id="missing-run",
                    coverage_raster_uri=(
                        "coverage-runs/missing-run/coverage.tif"
                    ),
                    display_geojson_path=path,
                    authoritative_coverage_area_sq_m=(
                        1000.0
                    ),
                    processing_time_seconds=1.0,
                )


if __name__ == "__main__":
    unittest.main()
    