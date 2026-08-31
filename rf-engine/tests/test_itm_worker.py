import json
import tempfile
import unittest
from pathlib import Path

from geovaris_rf.itm_worker import (
    P2108_CLUTTER_MODEL,
    P2108_CLUTTER_MODEL_VERSION,
    P2108_CORRECTION_END,
    _read_geojson_geometry,
    _run_uses_clutter,
    _validate_clutter_configuration,
)


def build_clutter_run() -> dict:
    """Return a valid clutter configuration snapshot."""

    return {
        "clutter_source": (
            "USGS/MRLC Annual NLCD Land Cover"
        ),
        "clutter_version": "2025 C1V2",
        "clutter_model": P2108_CLUTTER_MODEL,
        "clutter_model_version": (
            P2108_CLUTTER_MODEL_VERSION
        ),
        "clutter_percentage_locations": 50.0,
        "clutter_correction_end": (
            P2108_CORRECTION_END
        ),
    }


class TestClutterConfiguration(unittest.TestCase):
    def test_no_clutter_configuration_is_allowed(
        self,
    ) -> None:
        coverage_run = {
            "clutter_source": None,
            "clutter_version": None,
            "clutter_model": None,
            "clutter_model_version": None,
            "clutter_percentage_locations": None,
            "clutter_correction_end": None,
        }

        _validate_clutter_configuration(
            coverage_run
        )

        self.assertFalse(
            _run_uses_clutter(
                coverage_run
            )
        )

    def test_complete_supported_clutter_configuration_is_allowed(
        self,
    ) -> None:
        coverage_run = (
            build_clutter_run()
        )

        _validate_clutter_configuration(
            coverage_run
        )

        self.assertTrue(
            _run_uses_clutter(
                coverage_run
            )
        )

    def test_partial_clutter_configuration_is_rejected(
        self,
    ) -> None:
        coverage_run = (
            build_clutter_run()
        )

        coverage_run[
            "clutter_version"
        ] = None

        with self.assertRaisesRegex(
            ValueError,
            "incomplete clutter parameters",
        ):
            _validate_clutter_configuration(
                coverage_run
            )

    def test_unsupported_clutter_model_is_rejected(
        self,
    ) -> None:
        coverage_run = (
            build_clutter_run()
        )

        coverage_run[
            "clutter_model"
        ] = "unsupported-model"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported clutter model",
        ):
            _validate_clutter_configuration(
                coverage_run
            )

    def test_invalid_percentage_locations_is_rejected(
        self,
    ) -> None:
        coverage_run = (
            build_clutter_run()
        )

        coverage_run[
            "clutter_percentage_locations"
        ] = 100.0

        with self.assertRaisesRegex(
            ValueError,
            "percentage of locations",
        ):
            _validate_clutter_configuration(
                coverage_run
            )

    def test_non_receiver_correction_is_rejected(
        self,
    ) -> None:
        coverage_run = (
            build_clutter_run()
        )

        coverage_run[
            "clutter_correction_end"
        ] = "both"

        with self.assertRaisesRegex(
            ValueError,
            "receiver-side",
        ):
            _validate_clutter_configuration(
                coverage_run
            )


class TestCoverageGeoJsonGeometry(unittest.TestCase):
    def _write_geojson(
        self,
        document: dict,
        directory: str,
    ) -> Path:
        path = (
            Path(directory)
            / "coverage.geojson"
        )

        path.write_text(
            json.dumps(
                document
            ),
            encoding="utf-8",
        )

        return path

    def test_single_polygon_remains_polygon(
        self,
    ) -> None:
        polygon_coordinates = [
            [
                [-81.0, 28.0],
                [-80.9, 28.0],
                [-80.9, 28.1],
                [-81.0, 28.1],
                [-81.0, 28.0],
            ]
        ]

        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": (
                            polygon_coordinates
                        ),
                    },
                }
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = self._write_geojson(
                document,
                directory,
            )

            geometry = (
                _read_geojson_geometry(
                    path
                )
            )

        self.assertEqual(
            geometry["type"],
            "Polygon",
        )

        self.assertEqual(
            geometry["coordinates"],
            polygon_coordinates,
        )

    def test_multiple_polygon_features_become_multipolygon(
        self,
    ) -> None:
        first_polygon = [
            [
                [-81.0, 28.0],
                [-80.9, 28.0],
                [-80.9, 28.1],
                [-81.0, 28.1],
                [-81.0, 28.0],
            ]
        ]

        second_polygon = [
            [
                [-80.8, 28.0],
                [-80.7, 28.0],
                [-80.7, 28.1],
                [-80.8, 28.1],
                [-80.8, 28.0],
            ]
        ]

        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": (
                            first_polygon
                        ),
                    },
                },
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": (
                            second_polygon
                        ),
                    },
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = self._write_geojson(
                document,
                directory,
            )

            geometry = (
                _read_geojson_geometry(
                    path
                )
            )

        self.assertEqual(
            geometry["type"],
            "MultiPolygon",
        )

        self.assertEqual(
            geometry["coordinates"],
            [
                first_polygon,
                second_polygon,
            ],
        )

    def test_polygon_and_multipolygon_features_are_flattened(
        self,
    ) -> None:
        first_polygon = [
            [
                [-81.0, 28.0],
                [-80.9, 28.0],
                [-80.9, 28.1],
                [-81.0, 28.1],
                [-81.0, 28.0],
            ]
        ]

        second_polygon = [
            [
                [-80.8, 28.0],
                [-80.7, 28.0],
                [-80.7, 28.1],
                [-80.8, 28.1],
                [-80.8, 28.0],
            ]
        ]

        third_polygon = [
            [
                [-80.6, 28.0],
                [-80.5, 28.0],
                [-80.5, 28.1],
                [-80.6, 28.1],
                [-80.6, 28.0],
            ]
        ]

        document = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": (
                            first_polygon
                        ),
                    },
                },
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "MultiPolygon",
                        "coordinates": [
                            second_polygon,
                            third_polygon,
                        ],
                    },
                },
            ],
        }

        with tempfile.TemporaryDirectory() as directory:
            path = self._write_geojson(
                document,
                directory,
            )

            geometry = (
                _read_geojson_geometry(
                    path
                )
            )

        self.assertEqual(
            geometry["type"],
            "MultiPolygon",
        )

        self.assertEqual(
            geometry["coordinates"],
            [
                first_polygon,
                second_polygon,
                third_polygon,
            ],
        )


if __name__ == "__main__":
    unittest.main()