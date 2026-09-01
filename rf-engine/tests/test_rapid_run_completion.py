import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from geovaris_rf.rapid_run_completion import (
    POPULATION_ALLOCATION_METHOD,
    POPULATION_DATASET_SOURCE,
    POPULATION_DATASET_VERSION,
    POPULATION_DATASET_VINTAGE,
    POPULATION_GEOMETRY_BASIS,
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

            with patch(
                "geovaris_rf.rapid_run_completion.time.perf_counter",
                return_value=106.25,
            ):
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
                    processing_started_at=100.0,
                )

            self.assertEqual(
                cursor.execute.call_count,
                2,
            )

            first_call = (
                cursor.execute.call_args_list[
                    0
                ]
            )

            sql_text = (
                first_call[
                    0
                ][
                    0
                ]
            )

            params = (
                first_call[
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

            self.assertIn(
                "population_blocks",
                sql_text,
            )

            self.assertIn(
                "ST_Intersects",
                sql_text,
            )

            self.assertIn(
                "block_area_sq_m",
                sql_text,
            )

            self.assertIn(
                "covered_population",
                sql_text,
            )

            self.assertIn(
                "population_dataset_source",
                sql_text,
            )

            self.assertIn(
                "population_geometry_basis",
                sql_text,
            )

            self.assertIn(
                "WHERE coverage_fraction > 0",
                sql_text,
            )

            self.assertIn(
                "processing_time_seconds = NULL",
                sql_text,
            )

            self.assertEqual(
                params[
                    1
                ],
                POPULATION_DATASET_SOURCE,
            )

            self.assertEqual(
                params[
                    2
                ],
                POPULATION_DATASET_VERSION,
            )

            self.assertEqual(
                params[
                    3
                ],
                POPULATION_DATASET_VINTAGE,
            )

            self.assertEqual(
                params[
                    4
                ],
                RAPID_PROPAGATION_MODEL,
            )

            self.assertEqual(
                params[
                    5
                ],
                RAPID_PROPAGATION_MODEL_VERSION,
            )

            self.assertEqual(
                params[
                    7
                ],
                550_094_400.0,
            )

            self.assertEqual(
                params[
                    8
                ],
                str(
                    POPULATION_DATASET_VINTAGE
                ),
            )

            self.assertEqual(
                params[
                    9
                ],
                POPULATION_DATASET_SOURCE,
            )

            self.assertEqual(
                params[
                    10
                ],
                POPULATION_DATASET_VERSION,
            )

            self.assertEqual(
                params[
                    11
                ],
                POPULATION_ALLOCATION_METHOD,
            )

            self.assertEqual(
                params[
                    12
                ],
                POPULATION_GEOMETRY_BASIS,
            )

            self.assertEqual(
                params[
                    13
                ],
                "run-123",
            )

            second_call = (
                cursor.execute.call_args_list[
                    1
                ]
            )

            timing_sql = (
                second_call[
                    0
                ][
                    0
                ]
            )

            timing_params = (
                second_call[
                    0
                ][
                    1
                ]
            )

            self.assertIn(
                "processing_time_seconds = %s",
                timing_sql,
            )

            self.assertEqual(
                timing_params[
                    0
                ],
                6.25,
            )

            self.assertEqual(
                timing_params[
                    1
                ],
                "run-123",
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
                    processing_started_at=100.0,
                )

    def test_negative_processing_start_rejected(
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

            with self.assertRaisesRegex(
                ValueError,
                "processing_started_at",
            ):
                complete_rapid_run(
                    MagicMock(),
                    run_id="run-123",
                    coverage_raster_uri=(
                        "coverage-runs/run-123/coverage.tif"
                    ),
                    display_geojson_path=path,
                    authoritative_coverage_area_sq_m=(
                        1000.0
                    ),
                    processing_started_at=-1.0,
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
                "not updated",
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
                    processing_started_at=100.0,
                )

            self.assertEqual(
                cursor.execute.call_count,
                1,
            )

            connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()