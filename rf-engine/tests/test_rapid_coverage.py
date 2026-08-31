import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.rapid_coverage import (
    RAPID_COVERAGE_COVERED_VALUE,
    RAPID_COVERAGE_NODATA_VALUE,
    RAPID_COVERAGE_NOT_COVERED_VALUE,
    RapidCoverageResult,
    build_rapid_coverage_mask,
    build_rapid_coverage_raster,
)


class RapidCoverageTests(unittest.TestCase):
    def test_visible_cell_inside_range_is_covered(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        viewshed = np.ma.array(
            [
                [1],
            ],
            dtype=np.uint8,
        )

        result = build_rapid_coverage_mask(
            viewshed_values=viewshed,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            maximum_distance_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            RAPID_COVERAGE_COVERED_VALUE,
        )

    def test_visible_cell_outside_range_is_not_covered(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        viewshed = np.ma.array(
            [
                [1, 1],
            ],
            dtype=np.uint8,
        )

        result = build_rapid_coverage_mask(
            viewshed_values=viewshed,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            maximum_distance_m=20.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            RAPID_COVERAGE_COVERED_VALUE,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    1,
                ]
            ),
            RAPID_COVERAGE_NOT_COVERED_VALUE,
        )

    def test_not_visible_cell_is_not_covered(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        viewshed = np.ma.array(
            [
                [0],
            ],
            dtype=np.uint8,
        )

        result = build_rapid_coverage_mask(
            viewshed_values=viewshed,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            maximum_distance_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            RAPID_COVERAGE_NOT_COVERED_VALUE,
        )

    def test_masked_viewshed_cell_becomes_nodata(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        viewshed = np.ma.array(
            [
                [1, 1],
            ],
            mask=[
                [False, True],
            ],
            dtype=np.uint8,
        )

        result = build_rapid_coverage_mask(
            viewshed_values=viewshed,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            maximum_distance_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            RAPID_COVERAGE_COVERED_VALUE,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    1,
                ]
            ),
            RAPID_COVERAGE_NODATA_VALUE,
        )

    def test_invalid_viewshed_value_is_rejected(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        viewshed = np.ma.array(
            [
                [7],
            ],
            dtype=np.uint8,
        )

        with self.assertRaisesRegex(
            ValueError,
            "unsupported values",
        ):
            build_rapid_coverage_mask(
                viewshed_values=viewshed,
                transform=transform,
                observer_x_m=15.0,
                observer_y_m=15.0,
                maximum_distance_m=1000.0,
            )

    def test_nonpositive_distance_is_rejected(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        viewshed = np.ma.array(
            [
                [1],
            ],
            dtype=np.uint8,
        )

        with self.assertRaises(
            ValueError
        ):
            build_rapid_coverage_mask(
                viewshed_values=viewshed,
                transform=transform,
                observer_x_m=15.0,
                observer_y_m=15.0,
                maximum_distance_m=0.0,
            )

    def test_writes_single_band_rapid_raster(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            viewshed_path = (
                temp_path
                / "viewshed.tif"
            )

            output_path = (
                temp_path
                / "rapid.tif"
            )

            transform = from_origin(
                500000.0,
                3200060.0,
                30.0,
                30.0,
            )

            with rasterio.open(
                viewshed_path,
                "w",
                driver="GTiff",
                width=2,
                height=2,
                count=1,
                dtype="uint8",
                crs="EPSG:32617",
                transform=transform,
                nodata=255,
            ) as dataset:
                dataset.write(
                    np.array(
                        [
                            [1, 1],
                            [0, 1],
                        ],
                        dtype=np.uint8,
                    ),
                    1,
                )

            result = build_rapid_coverage_raster(
                viewshed_path=(
                    viewshed_path
                ),
                destination_path=(
                    output_path
                ),
                observer_latitude=(
                    28.92805708
                ),
                observer_longitude=(
                    -80.99984610
                ),
                frequency_mhz=900.0,
                eirp_dbm=40.0,
                receiver_threshold_dbm=(
                    -100.0
                ),
                calculation_radius_m=(
                    1000.0
                ),
            )

            self.assertIsInstance(
                result,
                RapidCoverageResult,
            )

            self.assertTrue(
                output_path.exists()
            )

            with rasterio.open(
                output_path
            ) as dataset:
                self.assertEqual(
                    dataset.count,
                    1,
                )

                self.assertEqual(
                    dataset.dtypes[
                        0
                    ],
                    "uint8",
                )

                self.assertEqual(
                    dataset.nodata,
                    255.0,
                )

                self.assertEqual(
                    dataset.crs.to_epsg(),
                    32617,
                )

    def test_fspl_range_is_limited_by_calculation_radius(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            viewshed_path = (
                temp_path
                / "viewshed.tif"
            )

            output_path = (
                temp_path
                / "rapid.tif"
            )

            transform = from_origin(
                500000.0,
                3200030.0,
                30.0,
                30.0,
            )

            with rasterio.open(
                viewshed_path,
                "w",
                driver="GTiff",
                width=1,
                height=1,
                count=1,
                dtype="uint8",
                crs="EPSG:32617",
                transform=transform,
                nodata=255,
            ) as dataset:
                dataset.write(
                    np.array(
                        [
                            [1],
                        ],
                        dtype=np.uint8,
                    ),
                    1,
                )

            result = build_rapid_coverage_raster(
                viewshed_path=(
                    viewshed_path
                ),
                destination_path=(
                    output_path
                ),
                observer_latitude=(
                    28.92805708
                ),
                observer_longitude=(
                    -80.99984610
                ),
                frequency_mhz=900.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=(
                    -120.0
                ),
                calculation_radius_m=(
                    1000.0
                ),
            )

            self.assertLessEqual(
                result.effective_maximum_distance_m,
                1000.0,
            )

    def test_lineage_tags_are_written(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            viewshed_path = (
                temp_path
                / "viewshed.tif"
            )

            output_path = (
                temp_path
                / "rapid.tif"
            )

            transform = from_origin(
                500000.0,
                3200030.0,
                30.0,
                30.0,
            )

            with rasterio.open(
                viewshed_path,
                "w",
                driver="GTiff",
                width=1,
                height=1,
                count=1,
                dtype="uint8",
                crs="EPSG:32617",
                transform=transform,
                nodata=255,
            ) as dataset:
                dataset.write(
                    np.array(
                        [
                            [1],
                        ],
                        dtype=np.uint8,
                    ),
                    1,
                )

            build_rapid_coverage_raster(
                viewshed_path=(
                    viewshed_path
                ),
                destination_path=(
                    output_path
                ),
                observer_latitude=(
                    28.92805708
                ),
                observer_longitude=(
                    -80.99984610
                ),
                frequency_mhz=900.0,
                eirp_dbm=40.0,
                receiver_threshold_dbm=(
                    -100.0
                ),
                calculation_radius_m=(
                    1000.0
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                tags = dataset.tags()

                self.assertEqual(
                    tags[
                        "analysis_method"
                    ],
                    "Rapid Coverage Estimate",
                )

                self.assertEqual(
                    tags[
                        "methodology"
                    ],
                    (
                        "Terrain/Clutter LOS + "
                        "Free-Space Link Budget"
                    ),
                )

                self.assertEqual(
                    tags[
                        "engineering_estimate"
                    ],
                    "true",
                )


if __name__ == "__main__":
    unittest.main()