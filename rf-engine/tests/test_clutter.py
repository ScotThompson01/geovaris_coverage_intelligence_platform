import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
    NlcdLandCoverClass,
    nlcd_class_to_clutter,
    sample_clutter,
    validate_nlcd_raster,
)


class ClutterTests(
    unittest.TestCase
):
    def _write_test_raster(
        self,
        path: Path,
        value: int = 22,
    ) -> None:
        data = np.full(
            (
                10,
                10,
            ),
            value,
            dtype=np.uint8,
        )

        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            width=10,
            height=10,
            count=1,
            dtype="uint8",
            crs="EPSG:32617",
            transform=from_origin(
                400000.0,
                3200000.0,
                30.0,
                30.0,
            ),
            nodata=250,
        ) as dataset:
            dataset.write(
                data,
                1,
            )

    def test_low_intensity_developed_maps_to_suburban(
        self,
    ):
        (
            source_class,
            clutter_class,
        ) = nlcd_class_to_clutter(
            22
        )

        self.assertEqual(
            source_class,
            NlcdLandCoverClass.DEVELOPED_LOW_INTENSITY,
        )

        self.assertEqual(
            clutter_class,
            GeoVarisClutterClass.SUBURBAN,
        )

    def test_forest_classes_map_to_forest(
        self,
    ):
        for value in (
            41,
            42,
            43,
        ):
            with self.subTest(
                value=value
            ):
                _, clutter_class = (
                    nlcd_class_to_clutter(
                        value
                    )
                )

                self.assertEqual(
                    clutter_class,
                    GeoVarisClutterClass.FOREST,
                )

    def test_agriculture_classes_map_to_agriculture(
        self,
    ):
        for value in (
            81,
            82,
        ):
            with self.subTest(
                value=value
            ):
                _, clutter_class = (
                    nlcd_class_to_clutter(
                        value
                    )
                )

                self.assertEqual(
                    clutter_class,
                    GeoVarisClutterClass.AGRICULTURE,
                )

    def test_unknown_nlcd_class_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            nlcd_class_to_clutter(
                99
            )

    def test_valid_nlcd_raster_metadata(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "clutter.tif"
            )

            self._write_test_raster(
                raster_path
            )

            metadata = (
                validate_nlcd_raster(
                    raster_path
                )
            )

            self.assertEqual(
                metadata.width,
                10,
            )

            self.assertEqual(
                metadata.height,
                10,
            )

            self.assertEqual(
                metadata.resolution_x_m,
                30.0,
            )

            self.assertEqual(
                metadata.resolution_y_m,
                30.0,
            )

            self.assertEqual(
                metadata.nodata_value,
                250.0,
            )

    def test_wrong_resolution_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = (
                Path(temp_dir)
                / "clutter.tif"
            )

            data = np.full(
                (
                    10,
                    10,
                ),
                22,
                dtype=np.uint8,
            )

            with rasterio.open(
                raster_path,
                "w",
                driver="GTiff",
                width=10,
                height=10,
                count=1,
                dtype="uint8",
                crs="EPSG:32617",
                transform=from_origin(
                    400000.0,
                    3200000.0,
                    60.0,
                    60.0,
                ),
                nodata=250,
            ) as dataset:
                dataset.write(
                    data,
                    1,
                )

            with self.assertRaises(
                ValueError
            ):
                validate_nlcd_raster(
                    raster_path
                )


if __name__ == "__main__":
    unittest.main()