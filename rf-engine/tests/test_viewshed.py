import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from rasterio.transform import from_origin

from geovaris_rf.terrain_analysis import (
    DEFAULT_K_FACTOR,
)
from geovaris_rf.viewshed import (
    GDAL_VIEWSHED_PATH_ENV,
    VIEWSHED_NODATA_VALUE,
    VIEWSHED_NOT_VISIBLE_VALUE,
    VIEWSHED_VISIBLE_VALUE,
    build_binary_viewshed_mask,
    k_factor_to_curvature_coefficient,
    resolve_gdal_viewshed_path,
)


class ViewshedTests(unittest.TestCase):
    def test_default_k_factor_maps_to_point_seven_five(
        self,
    ) -> None:
        result = (
            k_factor_to_curvature_coefficient(
                DEFAULT_K_FACTOR
            )
        )

        self.assertAlmostEqual(
            result,
            0.75,
            places=12,
        )

    def test_no_refraction_maps_to_one(
        self,
    ) -> None:
        result = (
            k_factor_to_curvature_coefficient(
                1.0
            )
        )

        self.assertEqual(
            result,
            1.0,
        )

    def test_invalid_k_factor_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ValueError
        ):
            k_factor_to_curvature_coefficient(
                0.0
            )

    def test_explicit_gdal_path_is_resolved(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = (
                Path(
                    temp_dir
                )
                / "gdal_viewshed.exe"
            )

            executable.write_text(
                "test"
            )

            result = (
                resolve_gdal_viewshed_path(
                    executable
                )
            )

            self.assertEqual(
                result,
                executable.resolve(),
            )

    def test_environment_gdal_path_is_resolved(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = (
                Path(
                    temp_dir
                )
                / "gdal_viewshed.exe"
            )

            executable.write_text(
                "test"
            )

            with patch.dict(
                os.environ,
                {
                    GDAL_VIEWSHED_PATH_ENV: str(
                        executable
                    )
                },
                clear=False,
            ):
                result = (
                    resolve_gdal_viewshed_path()
                )

            self.assertEqual(
                result,
                executable.resolve(),
            )

    def test_open_receiver_is_visible_when_required_height_is_met(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            60.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0, 100.0],
                [100.0, 100.0],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [100.0, 100.0],
                [100.0, 100.0],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [0.0, 1.0],
                [1.0, 1.0],
            ],
            dtype=np.float64,
        )

        result = build_binary_viewshed_mask(
            dem_values=dem,
            effective_surface_values=effective,
            minimum_target_height_values=minimum_height,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=45.0,
            receiver_height_agl_m=2.0,
            calculation_radius_m=1000.0,
        )

        self.assertTrue(
            np.all(
                result
                == VIEWSHED_VISIBLE_VALUE
            )
        )

    def test_destination_clutter_does_not_reduce_receiver_height(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [115.0],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [1.0],
            ],
            dtype=np.float64,
        )

        result = build_binary_viewshed_mask(
            dem_values=dem,
            effective_surface_values=effective,
            minimum_target_height_values=minimum_height,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            receiver_height_agl_m=2.0,
            calculation_radius_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            VIEWSHED_VISIBLE_VALUE,
        )

    def test_required_target_height_can_block_receiver(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [115.0],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [3.0],
            ],
            dtype=np.float64,
        )

        result = build_binary_viewshed_mask(
            dem_values=dem,
            effective_surface_values=effective,
            minimum_target_height_values=minimum_height,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            receiver_height_agl_m=2.0,
            calculation_radius_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            VIEWSHED_NOT_VISIBLE_VALUE,
        )

    def test_receiver_above_clutter_can_be_visible(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [110.0],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [4.0],
            ],
            dtype=np.float64,
        )

        result = build_binary_viewshed_mask(
            dem_values=dem,
            effective_surface_values=effective,
            minimum_target_height_values=minimum_height,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            receiver_height_agl_m=15.0,
            calculation_radius_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            VIEWSHED_VISIBLE_VALUE,
        )

    def test_cells_outside_radius_are_not_visible(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0, 100.0],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [100.0, 100.0],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [0.0, 0.0],
            ],
            dtype=np.float64,
        )

        result = build_binary_viewshed_mask(
            dem_values=dem,
            effective_surface_values=effective,
            minimum_target_height_values=minimum_height,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            receiver_height_agl_m=2.0,
            calculation_radius_m=20.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            VIEWSHED_VISIBLE_VALUE,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    1,
                ]
            ),
            VIEWSHED_NOT_VISIBLE_VALUE,
        )

    def test_masked_input_becomes_viewshed_nodata(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0, 100.0],
            ],
            mask=[
                [False, True],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [100.0, 100.0],
            ],
            mask=[
                [False, True],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [0.0, 0.0],
            ],
            mask=[
                [False, False],
            ],
            dtype=np.float64,
        )

        result = build_binary_viewshed_mask(
            dem_values=dem,
            effective_surface_values=effective,
            minimum_target_height_values=minimum_height,
            transform=transform,
            observer_x_m=15.0,
            observer_y_m=15.0,
            receiver_height_agl_m=2.0,
            calculation_radius_m=1000.0,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    0,
                ]
            ),
            VIEWSHED_VISIBLE_VALUE,
        )

        self.assertEqual(
            int(
                result[
                    0,
                    1,
                ]
            ),
            VIEWSHED_NODATA_VALUE,
        )

    def test_effective_surface_below_dem_is_rejected(
        self,
    ) -> None:
        transform = from_origin(
            0.0,
            30.0,
            30.0,
            30.0,
        )

        dem = np.ma.array(
            [
                [100.0],
            ],
            dtype=np.float32,
        )

        effective = np.ma.array(
            [
                [90.0],
            ],
            dtype=np.float32,
        )

        minimum_height = np.ma.array(
            [
                [0.0],
            ],
            dtype=np.float64,
        )

        with self.assertRaisesRegex(
            ValueError,
            "below the DEM",
        ):
            build_binary_viewshed_mask(
                dem_values=dem,
                effective_surface_values=effective,
                minimum_target_height_values=minimum_height,
                transform=transform,
                observer_x_m=15.0,
                observer_y_m=15.0,
                receiver_height_agl_m=2.0,
                calculation_radius_m=1000.0,
            )


if __name__ == "__main__":
    unittest.main()