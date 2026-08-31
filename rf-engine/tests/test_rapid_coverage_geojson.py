import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.rapid_coverage_geojson import (
    DEFAULT_DISPLAY_COORDINATE_PRECISION,
    DEFAULT_DISPLAY_MINIMUM_COMPONENT_AREA_M2,
    RapidCoverageGeoJsonResult,
    rapid_coverage_raster_to_geojson,
)


class RapidCoverageGeoJsonTests(
    unittest.TestCase
):
    def _write_test_raster(
        self,
        path: Path,
        *,
        include_coverage: bool = True,
        invalid_value: bool = False,
    ) -> None:
        coverage = np.zeros(
            (
                4,
                4,
            ),
            dtype=np.uint8,
        )

        if include_coverage:
            coverage[
                1,
                1,
            ] = 1

            coverage[
                1,
                2,
            ] = 1

            coverage[
                3,
                3,
            ] = 1

        if invalid_value:
            coverage[
                0,
                0,
            ] = 7

        transform = from_origin(
            500000.0,
            3200000.0,
            30.0,
            30.0,
        )

        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=4,
            height=4,
            count=1,
            dtype="uint8",
            crs="EPSG:32617",
            transform=transform,
            nodata=255,
        ) as dataset:
            dataset.write(
                coverage,
                1,
            )

            dataset.update_tags(
                product=(
                    "GeoVaris Coverage Intelligence"
                ),
                output_type=(
                    "rapid_coverage_raster"
                ),
                analysis_method=(
                    "Rapid Coverage Estimate"
                ),
                methodology=(
                    "Terrain/Clutter LOS + "
                    "Free-Space Link Budget"
                ),
                engineering_estimate="true",
            )

    def test_missing_raster_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            FileNotFoundError
        ):
            rapid_coverage_raster_to_geojson(
                raster_path=(
                    "missing-rapid.tif"
                ),
                output_path=(
                    "rapid.geojson"
                ),
            )

    def test_geojson_file_is_written(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                rapid_coverage_raster_to_geojson(
                    raster_path=(
                        raster_path
                    ),
                    output_path=(
                        output_path
                    ),
                    minimum_component_area_m2=0.0,
                )
            )

            self.assertIsInstance(
                result,
                RapidCoverageGeoJsonResult,
            )

            self.assertTrue(
                output_path.exists()
            )

    def test_output_is_feature_collection(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            rapid_coverage_raster_to_geojson(
                raster_path=raster_path,
                output_path=output_path,
                minimum_component_area_m2=0.0,
            )

            document = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            self.assertEqual(
                document[
                    "type"
                ],
                "FeatureCollection",
            )

            self.assertGreater(
                len(
                    document[
                        "features"
                    ]
                ),
                0,
            )

    def test_output_geometry_is_epsg_4326(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            rapid_coverage_raster_to_geojson(
                raster_path=raster_path,
                output_path=output_path,
                minimum_component_area_m2=0.0,
            )

            document = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            geometry = (
                document[
                    "features"
                ][0][
                    "geometry"
                ]
            )

            self.assertIn(
                geometry[
                    "type"
                ],
                (
                    "Polygon",
                    "MultiPolygon",
                ),
            )

    def test_rapid_lineage_is_preserved(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                    minimum_component_area_m2=0.0,
                )
            )

            self.assertEqual(
                result.analysis_method,
                "Rapid Coverage Estimate",
            )

            self.assertEqual(
                result.methodology,
                (
                    "Terrain/Clutter LOS + "
                    "Free-Space Link Budget"
                ),
            )

            self.assertEqual(
                result.source_crs,
                "EPSG:32617",
            )

            self.assertEqual(
                result.output_crs,
                "EPSG:4326",
            )

    def test_authoritative_area_comes_from_all_covered_cells(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                    minimum_component_area_m2=0.0,
                )
            )

            self.assertEqual(
                result.covered_cell_count,
                3,
            )

            self.assertEqual(
                result.authoritative_covered_area_m2,
                2700.0,
            )

            self.assertAlmostEqual(
                result.authoritative_covered_area_km2,
                0.0027,
                places=12,
            )

    def test_display_filter_does_not_change_authoritative_area(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                    minimum_component_area_m2=1800.0,
                )
            )

            self.assertEqual(
                result.covered_cell_count,
                3,
            )

            self.assertEqual(
                result.authoritative_covered_area_m2,
                2700.0,
            )

            self.assertEqual(
                result.display_retained_area_m2,
                1800.0,
            )

            self.assertAlmostEqual(
                result.display_retained_area_percent,
                66.6666666667,
                places=6,
            )

            self.assertEqual(
                result.feature_count,
                1,
            )

    def test_collection_contains_authoritative_and_display_metadata(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            rapid_coverage_raster_to_geojson(
                raster_path=raster_path,
                output_path=output_path,
                minimum_component_area_m2=1800.0,
                coordinate_precision=5,
            )

            document = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            properties = document[
                "properties"
            ]

            self.assertEqual(
                properties[
                    "authoritative_covered_area_m2"
                ],
                2700.0,
            )

            self.assertEqual(
                properties[
                    "display_retained_area_m2"
                ],
                1800.0,
            )

            self.assertEqual(
                properties[
                    "minimum_component_area_m2"
                ],
                1800.0,
            )

            self.assertEqual(
                properties[
                    "coordinate_precision"
                ],
                5,
            )

    def test_default_display_settings_are_recorded(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                )
            )

            self.assertEqual(
                result.minimum_component_area_m2,
                DEFAULT_DISPLAY_MINIMUM_COMPONENT_AREA_M2,
            )

            self.assertEqual(
                result.coordinate_precision,
                DEFAULT_DISPLAY_COORDINATE_PRECISION,
            )

    def test_no_covered_cells_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path,
                include_coverage=False,
            )

            with self.assertRaises(
                ValueError
            ):
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                )

    def test_invalid_raster_value_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path,
                invalid_value=True,
            )

            with self.assertRaisesRegex(
                ValueError,
                "unsupported values",
            ):
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                )

    def test_negative_minimum_component_area_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "rapid.tif"
            )

            output_path = (
                Path(temp_dir)
                / "rapid.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            with self.assertRaises(
                ValueError
            ):
                rapid_coverage_raster_to_geojson(
                    raster_path=raster_path,
                    output_path=output_path,
                    minimum_component_area_m2=-1.0,
                )


if __name__ == "__main__":
    unittest.main()