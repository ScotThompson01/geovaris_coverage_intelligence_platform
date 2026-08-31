import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
    NLCD_NODATA_VALUE,
)
from geovaris_rf.clutter_height import (
    build_geovaris_default_clutter_height_profile,
)
from geovaris_rf.dem_raster import (
    DEFAULT_DEM_NODATA,
)
from geovaris_rf.effective_surface import (
    build_clutter_height_array,
    build_effective_surface_raster,
)


class EffectiveSurfaceTests(unittest.TestCase):
    def test_clutter_height_array_maps_known_classes(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        values = np.array(
            [
                [11, 22],
                [23, 41],
            ],
            dtype=np.uint8,
        )

        result = build_clutter_height_array(
            nlcd_values=values,
            profile=profile,
        )

        expected = np.array(
            [
                [0.0, 10.0],
                [12.0, 15.0],
            ],
            dtype=np.float32,
        )

        np.testing.assert_array_equal(
            result.data,
            expected,
        )

        self.assertFalse(
            np.any(
                result.mask
            )
        )

    def test_clutter_height_array_masks_nodata(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        values = np.array(
            [
                [11, NLCD_NODATA_VALUE],
            ],
            dtype=np.uint8,
        )

        result = build_clutter_height_array(
            nlcd_values=values,
            profile=profile,
        )

        self.assertFalse(
            bool(
                result.mask[0, 0]
            )
        )

        self.assertTrue(
            bool(
                result.mask[0, 1]
            )
        )

    def test_clutter_height_array_rejects_unknown_class(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        values = np.array(
            [
                [11, 99],
            ],
            dtype=np.uint8,
        )

        with self.assertRaisesRegex(
            ValueError,
            "unsupported land-cover class values: 99",
        ):
            build_clutter_height_array(
                nlcd_values=values,
                profile=profile,
            )

    def test_clutter_height_array_requires_two_dimensions(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        values = np.array(
            [11, 22, 41],
            dtype=np.uint8,
        )

        with self.assertRaisesRegex(
            ValueError,
            "two-dimensional",
        ):
            build_clutter_height_array(
                nlcd_values=values,
                profile=profile,
            )

    def test_clutter_height_array_requires_integer_values(
        self,
    ) -> None:
        profile = (
            build_geovaris_default_clutter_height_profile()
        )

        values = np.array(
            [
                [11.0, 22.0],
            ],
            dtype=np.float32,
        )

        with self.assertRaisesRegex(
            ValueError,
            "integer data type",
        ):
            build_clutter_height_array(
                nlcd_values=values,
                profile=profile,
            )

    def test_effective_surface_adds_clutter_to_dem(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            dem_path = (
                temp_path
                / "dem.tif"
            )

            clutter_path = (
                temp_path
                / "nlcd.tif"
            )

            output_path = (
                temp_path
                / "effective_surface.tif"
            )

            transform = from_origin(
                500000.0,
                3200000.0,
                30.0,
                30.0,
            )

            dem_values = np.array(
                [
                    [100.0, 100.0],
                    [100.0, 100.0],
                ],
                dtype=np.float32,
            )

            nlcd_values = np.array(
                [
                    [11, 22],
                    [23, 41],
                ],
                dtype=np.uint8,
            )

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                dtype="float32",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=2,
                height=2,
                nodata=DEFAULT_DEM_NODATA,
            ) as dst:
                dst.write(
                    dem_values,
                    1,
                )

            with rasterio.open(
                clutter_path,
                "w",
                driver="GTiff",
                dtype="uint8",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=2,
                height=2,
                nodata=NLCD_NODATA_VALUE,
            ) as dst:
                dst.write(
                    nlcd_values,
                    1,
                )

            result = build_effective_surface_raster(
                dem_path=dem_path,
                clutter_raster_path=(
                    clutter_path
                ),
                destination_path=(
                    output_path
                ),
                clutter_profile=(
                    build_geovaris_default_clutter_height_profile()
                ),
            )

            self.assertTrue(
                output_path.exists()
            )

            self.assertEqual(
                result.target_crs,
                "EPSG:32617",
            )

            self.assertEqual(
                result.width_px,
                2,
            )

            self.assertEqual(
                result.height_px,
                2,
            )

            self.assertEqual(
                result.minimum_clutter_height_m,
                0.0,
            )

            self.assertEqual(
                result.maximum_clutter_height_m,
                15.0,
            )

            with rasterio.open(
                output_path
            ) as src:
                actual = src.read(
                    1
                )

                expected = np.array(
                    [
                        [100.0, 110.0],
                        [112.0, 115.0],
                    ],
                    dtype=np.float32,
                )

                np.testing.assert_array_equal(
                    actual,
                    expected,
                )

    def test_effective_surface_preserves_dem_grid(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            dem_path = (
                temp_path
                / "dem.tif"
            )

            clutter_path = (
                temp_path
                / "nlcd.tif"
            )

            output_path = (
                temp_path
                / "effective_surface.tif"
            )

            transform = from_origin(
                500000.0,
                3200000.0,
                30.0,
                30.0,
            )

            dem_values = np.full(
                (
                    2,
                    3,
                ),
                50.0,
                dtype=np.float32,
            )

            nlcd_values = np.full(
                (
                    2,
                    3,
                ),
                11,
                dtype=np.uint8,
            )

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                dtype="float32",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=3,
                height=2,
                nodata=DEFAULT_DEM_NODATA,
            ) as dst:
                dst.write(
                    dem_values,
                    1,
                )

            with rasterio.open(
                clutter_path,
                "w",
                driver="GTiff",
                dtype="uint8",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=3,
                height=2,
                nodata=NLCD_NODATA_VALUE,
            ) as dst:
                dst.write(
                    nlcd_values,
                    1,
                )

            build_effective_surface_raster(
                dem_path=dem_path,
                clutter_raster_path=(
                    clutter_path
                ),
                destination_path=(
                    output_path
                ),
                clutter_profile=(
                    build_geovaris_default_clutter_height_profile()
                ),
            )

            with (
                rasterio.open(
                    dem_path
                ) as dem,
                rasterio.open(
                    output_path
                ) as output,
            ):
                self.assertEqual(
                    output.crs,
                    dem.crs,
                )

                self.assertEqual(
                    output.transform,
                    dem.transform,
                )

                self.assertEqual(
                    output.width,
                    dem.width,
                )

                self.assertEqual(
                    output.height,
                    dem.height,
                )

                self.assertEqual(
                    output.res,
                    dem.res,
                )

                self.assertEqual(
                    output.nodata,
                    DEFAULT_DEM_NODATA,
                )

                self.assertEqual(
                    output.dtypes[0],
                    "float32",
                )

    def test_dem_nodata_propagates_to_effective_surface(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            dem_path = (
                temp_path
                / "dem.tif"
            )

            clutter_path = (
                temp_path
                / "nlcd.tif"
            )

            output_path = (
                temp_path
                / "effective_surface.tif"
            )

            transform = from_origin(
                500000.0,
                3200000.0,
                30.0,
                30.0,
            )

            dem_values = np.array(
                [
                    [100.0, DEFAULT_DEM_NODATA],
                ],
                dtype=np.float32,
            )

            nlcd_values = np.array(
                [
                    [41, 41],
                ],
                dtype=np.uint8,
            )

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                dtype="float32",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=2,
                height=1,
                nodata=DEFAULT_DEM_NODATA,
            ) as dst:
                dst.write(
                    dem_values,
                    1,
                )

            with rasterio.open(
                clutter_path,
                "w",
                driver="GTiff",
                dtype="uint8",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=2,
                height=1,
                nodata=NLCD_NODATA_VALUE,
            ) as dst:
                dst.write(
                    nlcd_values,
                    1,
                )

            build_effective_surface_raster(
                dem_path=dem_path,
                clutter_raster_path=(
                    clutter_path
                ),
                destination_path=(
                    output_path
                ),
                clutter_profile=(
                    build_geovaris_default_clutter_height_profile()
                ),
            )

            with rasterio.open(
                output_path
            ) as src:
                actual = src.read(
                    1
                )

                self.assertEqual(
                    float(
                        actual[0, 0]
                    ),
                    115.0,
                )

                self.assertEqual(
                    float(
                        actual[0, 1]
                    ),
                    DEFAULT_DEM_NODATA,
                )

    def test_nlcd_nodata_propagates_to_effective_surface(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            dem_path = (
                temp_path
                / "dem.tif"
            )

            clutter_path = (
                temp_path
                / "nlcd.tif"
            )

            output_path = (
                temp_path
                / "effective_surface.tif"
            )

            transform = from_origin(
                500000.0,
                3200000.0,
                30.0,
                30.0,
            )

            dem_values = np.array(
                [
                    [100.0, 100.0],
                ],
                dtype=np.float32,
            )

            nlcd_values = np.array(
                [
                    [41, NLCD_NODATA_VALUE],
                ],
                dtype=np.uint8,
            )

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                dtype="float32",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=2,
                height=1,
                nodata=DEFAULT_DEM_NODATA,
            ) as dst:
                dst.write(
                    dem_values,
                    1,
                )

            with rasterio.open(
                clutter_path,
                "w",
                driver="GTiff",
                dtype="uint8",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=2,
                height=1,
                nodata=NLCD_NODATA_VALUE,
            ) as dst:
                dst.write(
                    nlcd_values,
                    1,
                )

            build_effective_surface_raster(
                dem_path=dem_path,
                clutter_raster_path=(
                    clutter_path
                ),
                destination_path=(
                    output_path
                ),
                clutter_profile=(
                    build_geovaris_default_clutter_height_profile()
                ),
            )

            with rasterio.open(
                output_path
            ) as src:
                actual = src.read(
                    1
                )

                self.assertEqual(
                    float(
                        actual[0, 0]
                    ),
                    115.0,
                )

                self.assertEqual(
                    float(
                        actual[0, 1]
                    ),
                    DEFAULT_DEM_NODATA,
                )

    def test_result_preserves_clutter_profile_lineage(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            dem_path = (
                temp_path
                / "dem.tif"
            )

            clutter_path = (
                temp_path
                / "nlcd.tif"
            )

            output_path = (
                temp_path
                / "effective_surface.tif"
            )

            transform = from_origin(
                500000.0,
                3200000.0,
                30.0,
                30.0,
            )

            dem_values = np.array(
                [
                    [100.0],
                ],
                dtype=np.float32,
            )

            nlcd_values = np.array(
                [
                    [41],
                ],
                dtype=np.uint8,
            )

            with rasterio.open(
                dem_path,
                "w",
                driver="GTiff",
                dtype="float32",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=1,
                height=1,
                nodata=DEFAULT_DEM_NODATA,
            ) as dst:
                dst.write(
                    dem_values,
                    1,
                )

            with rasterio.open(
                clutter_path,
                "w",
                driver="GTiff",
                dtype="uint8",
                count=1,
                crs="EPSG:32617",
                transform=transform,
                width=1,
                height=1,
                nodata=NLCD_NODATA_VALUE,
            ) as dst:
                dst.write(
                    nlcd_values,
                    1,
                )

            profile = (
                build_geovaris_default_clutter_height_profile()
            )

            result = build_effective_surface_raster(
                dem_path=dem_path,
                clutter_raster_path=(
                    clutter_path
                ),
                destination_path=(
                    output_path
                ),
                clutter_profile=profile,
            )

            self.assertEqual(
                result.clutter_profile_name,
                profile.name,
            )

            self.assertEqual(
                result.clutter_profile_version,
                profile.version,
            )

            self.assertEqual(
                result.clutter_profile_source,
                profile.source,
            )

            self.assertEqual(
                result.clutter_height_units,
                "m",
            )


if __name__ == "__main__":
    unittest.main()