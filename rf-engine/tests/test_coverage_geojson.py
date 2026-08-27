import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.coverage_geojson import (
    CoverageGeoJsonResult,
    coverage_raster_to_geojson,
)


class CoverageGeoJsonTests(
    unittest.TestCase
):
    def _write_test_raster(
        self,
        path: Path,
        *,
        include_coverage: bool = True,
    ) -> None:
        nodata = -9999.0

        received_power = np.full(
            (
                3,
                3,
            ),
            nodata,
            dtype=np.float32,
        )

        margin = np.full(
            (
                3,
                3,
            ),
            nodata,
            dtype=np.float32,
        )

        coverage = np.full(
            (
                3,
                3,
            ),
            nodata,
            dtype=np.float32,
        )

        if include_coverage:
            received_power[
                1,
                1,
            ] = -70.0

            received_power[
                1,
                2,
            ] = -75.0

            margin[
                1,
                1,
            ] = 20.0

            margin[
                1,
                2,
            ] = 15.0

            coverage[
                1,
                1,
            ] = 1.0

            coverage[
                1,
                2,
            ] = 1.0

        transform = from_origin(
            500000.0,
            3200000.0,
            100.0,
            100.0,
        )

        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=3,
            height=3,
            count=3,
            dtype="float32",
            crs="EPSG:32617",
            transform=transform,
            nodata=nodata,
        ) as dataset:
            dataset.write(
                received_power,
                1,
            )

            dataset.write(
                margin,
                2,
            )

            dataset.write(
                coverage,
                3,
            )

            dataset.update_tags(
                product=(
                    "GeoVaris Coverage Intelligence"
                ),
                model_name="NTIA ITM",
                model_version="1.4",
                engineering_estimate="true",
            )

    def test_missing_raster_rejected(
        self,
    ):
        with self.assertRaises(
            FileNotFoundError
        ):
            coverage_raster_to_geojson(
                raster_path=(
                    "missing-coverage.tif"
                ),
                output_path=(
                    "coverage.geojson"
                ),
            )

    def test_geojson_file_is_written(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            output_path = (
                Path(temp_dir)
                / "coverage.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                coverage_raster_to_geojson(
                    raster_path=str(
                        raster_path
                    ),
                    output_path=str(
                        output_path
                    ),
                )
            )

            self.assertIsInstance(
                result,
                CoverageGeoJsonResult,
            )

            self.assertTrue(
                output_path.exists()
            )

    def test_output_is_feature_collection(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            output_path = (
                Path(temp_dir)
                / "coverage.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            coverage_raster_to_geojson(
                raster_path=str(
                    raster_path
                ),
                output_path=str(
                    output_path
                ),
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
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            output_path = (
                Path(temp_dir)
                / "coverage.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            coverage_raster_to_geojson(
                raster_path=str(
                    raster_path
                ),
                output_path=str(
                    output_path
                ),
            )

            document = json.loads(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            geometry = document[
                "features"
            ][0][
                "geometry"
            ]

            self.assertIn(
                geometry[
                    "type"
                ],
                (
                    "Polygon",
                    "MultiPolygon",
                ),
            )

            first_coordinate = (
                geometry[
                    "coordinates"
                ][0][0]
            )

            longitude = (
                first_coordinate[0]
            )

            latitude = (
                first_coordinate[1]
            )

            self.assertGreaterEqual(
                longitude,
                -180.0,
            )

            self.assertLessEqual(
                longitude,
                180.0,
            )

            self.assertGreaterEqual(
                latitude,
                -90.0,
            )

            self.assertLessEqual(
                latitude,
                90.0,
            )

    def test_model_lineage_is_preserved(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            output_path = (
                Path(temp_dir)
                / "coverage.geojson"
            )

            self._write_test_raster(
                raster_path
            )

            result = (
                coverage_raster_to_geojson(
                    raster_path=str(
                        raster_path
                    ),
                    output_path=str(
                        output_path
                    ),
                )
            )

            self.assertEqual(
                result.model_name,
                "NTIA ITM",
            )

            self.assertEqual(
                result.model_version,
                "1.4",
            )

            self.assertEqual(
                result.source_crs,
                "EPSG:32617",
            )

            self.assertEqual(
                result.output_crs,
                "EPSG:4326",
            )

    def test_no_covered_cells_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            output_path = (
                Path(temp_dir)
                / "coverage.geojson"
            )

            self._write_test_raster(
                raster_path,
                include_coverage=False,
            )

            with self.assertRaises(
                ValueError
            ):
                coverage_raster_to_geojson(
                    raster_path=str(
                        raster_path
                    ),
                    output_path=str(
                        output_path
                    ),
                )


if __name__ == "__main__":
    unittest.main()