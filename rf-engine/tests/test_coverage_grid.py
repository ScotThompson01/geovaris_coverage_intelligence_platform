import unittest

from geovaris_rf.coverage_grid import (
    CoverageGridPlan,
    CoverageGridPoint,
    plan_coverage_grid,
)


class CoverageGridTests(
    unittest.TestCase
):
    def test_invalid_latitude_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            plan_coverage_grid(
                91.0,
                -81.3792,
                5000.0,
                250.0,
            )

    def test_invalid_longitude_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            plan_coverage_grid(
                28.5383,
                -181.0,
                5000.0,
                250.0,
            )

    def test_zero_radius_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            plan_coverage_grid(
                28.5383,
                -81.3792,
                0.0,
                250.0,
            )

    def test_negative_resolution_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            plan_coverage_grid(
                28.5383,
                -81.3792,
                5000.0,
                -250.0,
            )

    def test_orlando_uses_utm_zone_17_north(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        self.assertEqual(
            grid.crs_epsg,
            32617,
        )

    def test_grid_plan_type(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        self.assertIsInstance(
            grid,
            CoverageGridPlan,
        )

    def test_5km_250m_grid_is_41_by_41(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        self.assertEqual(
            grid.width,
            41,
        )

        self.assertEqual(
            grid.height,
            41,
        )

        self.assertEqual(
            grid.total_cell_count,
            1681,
        )

    def test_grid_extent_matches_resolution(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        self.assertAlmostEqual(
            grid.east_m
            - grid.west_m,
            grid.width
            * grid.resolution_m,
        )

        self.assertAlmostEqual(
            grid.north_m
            - grid.south_m,
            grid.height
            * grid.resolution_m,
        )

    def test_center_cell_is_site_location(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        center_row = (
            grid.height // 2
        )

        center_column = (
            grid.width // 2
        )

        center = next(
            point
            for point in grid.points
            if (
                point.row
                == center_row
                and point.column
                == center_column
            )
        )

        self.assertAlmostEqual(
            center.x_m,
            grid.site_x_m,
            places=6,
        )

        self.assertAlmostEqual(
            center.y_m,
            grid.site_y_m,
            places=6,
        )

        self.assertAlmostEqual(
            center.distance_from_site_m,
            0.0,
            places=6,
        )

        self.assertTrue(
            center.inside_radius
        )

    def test_points_are_grid_point_objects(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        self.assertIsInstance(
            grid.points[0],
            CoverageGridPoint,
        )

    def test_inside_radius_count_is_less_than_total(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        self.assertGreater(
            grid.inside_radius_count,
            0,
        )

        self.assertLess(
            grid.inside_radius_count,
            grid.total_cell_count,
        )

    def test_corner_cell_is_outside_radius(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        corner = next(
            point
            for point in grid.points
            if (
                point.row == 0
                and point.column == 0
            )
        )

        self.assertFalse(
            corner.inside_radius
        )

    def test_center_lat_lon_matches_site(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        center = next(
            point
            for point in grid.points
            if (
                point.row
                == grid.height // 2
                and point.column
                == grid.width // 2
            )
        )

        self.assertAlmostEqual(
            center.latitude,
            28.5383,
            places=6,
        )

        self.assertAlmostEqual(
            center.longitude,
            -81.3792,
            places=6,
        )

    def test_rows_run_north_to_south(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        first_row_point = next(
            point
            for point in grid.points
            if (
                point.row == 0
                and point.column
                == grid.width // 2
            )
        )

        last_row_point = next(
            point
            for point in grid.points
            if (
                point.row
                == grid.height - 1
                and point.column
                == grid.width // 2
            )
        )

        self.assertGreater(
            first_row_point.y_m,
            last_row_point.y_m,
        )

    def test_columns_run_west_to_east(
        self,
    ):
        grid = plan_coverage_grid(
            28.5383,
            -81.3792,
            5000.0,
            250.0,
        )

        west_point = next(
            point
            for point in grid.points
            if (
                point.row
                == grid.height // 2
                and point.column == 0
            )
        )

        east_point = next(
            point
            for point in grid.points
            if (
                point.row
                == grid.height // 2
                and point.column
                == grid.width - 1
            )
        )

        self.assertLess(
            west_point.x_m,
            east_point.x_m,
        )


if __name__ == "__main__":
    unittest.main()