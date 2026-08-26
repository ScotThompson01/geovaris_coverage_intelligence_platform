import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from geovaris_rf.dem_raster import (
    DEFAULT_DEM_NODATA,
    DemDownloadResult,
    DemExportResult,
    DemMosaicResult,
    DemRasterInfo,
    DemReprojectionResult,
    DemTilePlan,
    TerrainGridPlan,
    build_3dep_export_url,
    calculate_geographic_bounding_box,
    calculate_utm_epsg,
    mosaic_dem_tiles,
    plan_dem_tiles,
    plan_terrain_grid,
    validate_radius,
)


class DemRasterTests(unittest.TestCase):
    def test_positive_radius_is_valid(self):
        validate_radius(1000.0)

    def test_zero_radius_rejected(self):
        with self.assertRaises(ValueError):
            validate_radius(0.0)

    def test_negative_radius_rejected(self):
        with self.assertRaises(ValueError):
            validate_radius(-100.0)

    def test_orlando_50_km_bounding_box(self):
        bounds = calculate_geographic_bounding_box(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
        )

        self.assertLess(
            bounds.west,
            -81.3792,
        )

        self.assertGreater(
            bounds.east,
            -81.3792,
        )

        self.assertLess(
            bounds.south,
            28.5383,
        )

        self.assertGreater(
            bounds.north,
            28.5383,
        )

    def test_invalid_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            calculate_geographic_bounding_box(
                latitude=95.0,
                longitude=-81.3792,
                radius_m=50_000.0,
            )

    def test_build_3dep_export_url(self):
        bounds = calculate_geographic_bounding_box(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
        )

        url = build_3dep_export_url(
            bounds=bounds,
            width_px=1000,
            height_px=1000,
        )

        self.assertIn(
            "3DEPElevation/ImageServer/exportImage",
            url,
        )

        self.assertIn(
            "bboxSR=4326",
            url,
        )

        self.assertIn(
            "imageSR=3857",
            url,
        )

        self.assertIn(
            "size=1000%2C1000",
            url,
        )

    def test_invalid_export_size_rejected(self):
        bounds = calculate_geographic_bounding_box(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
        )

        with self.assertRaises(ValueError):
            build_3dep_export_url(
                bounds=bounds,
                width_px=0,
                height_px=1000,
            )

    def test_dem_export_result_preserves_metadata(self):
        result = DemExportResult(
            href="https://example.com/test.tif",
            width=1000,
            height=1000,
            extent={
                "xmin": 1.0,
                "ymin": 2.0,
                "xmax": 3.0,
                "ymax": 4.0,
            },
        )

        self.assertEqual(
            result.width,
            1000,
        )

    def test_dem_download_result_preserves_metadata(self):
        result = DemDownloadResult(
            file_path="test.tif",
            size_bytes=12345,
            source_href="https://example.com",
        )

        self.assertEqual(
            result.size_bytes,
            12345,
        )

    def test_dem_raster_info_preserves_metadata(self):
        info = DemRasterInfo(
            file_path="test.tif",
            crs="EPSG:3857",
            width=1000,
            height=1000,
            pixel_size_x=30.0,
            pixel_size_y=30.0,
            data_type="float32",
            nodata=None,
            min_elevation_m=0.0,
            max_elevation_m=100.0,
            mean_elevation_m=50.0,
        )

        self.assertEqual(
            info.crs,
            "EPSG:3857",
        )

    def test_dem_reprojection_result_preserves_metadata(self):
        result = DemReprojectionResult(
            source_path="source.tif",
            destination_path="destination.tif",
            source_crs="EPSG:3857",
            target_crs="EPSG:32617",
            resolution_m=30.0,
            width_px=3334,
            height_px=3334,
            resampling_method="bilinear",
        )

        self.assertEqual(
            result.target_crs,
            "EPSG:32617",
        )

    def test_dem_mosaic_result_preserves_metadata(self):
        result = DemMosaicResult(
            destination_path="mosaic.tif",
            target_crs="EPSG:32617",
            resolution_m=30.0,
            width_px=3334,
            height_px=3334,
            tile_count=4,
            nodata=DEFAULT_DEM_NODATA,
        )

        self.assertEqual(
            result.tile_count,
            4,
        )

        self.assertEqual(
            result.nodata,
            -9999.0,
        )

    def test_orlando_uses_utm_zone_17_north(self):
        epsg = calculate_utm_epsg(
            latitude=28.5383,
            longitude=-81.3792,
        )

        self.assertEqual(
            epsg,
            32617,
        )

    def test_50km_30m_terrain_grid(self):
        plan = plan_terrain_grid(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
            resolution_m=30.0,
        )

        self.assertEqual(
            plan.target_crs,
            "EPSG:32617",
        )

        self.assertEqual(
            plan.width_px,
            3334,
        )

        self.assertEqual(
            plan.height_px,
            3334,
        )

    def test_terrain_grid_extent_matches_resolution(self):
        plan = plan_terrain_grid(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
            resolution_m=30.0,
        )

        self.assertAlmostEqual(
            plan.east_m - plan.west_m,
            plan.width_px * plan.resolution_m,
        )

        self.assertAlmostEqual(
            plan.north_m - plan.south_m,
            plan.height_px * plan.resolution_m,
        )

    def test_invalid_terrain_resolution_rejected(self):
        with self.assertRaises(ValueError):
            plan_terrain_grid(
                latitude=28.5383,
                longitude=-81.3792,
                radius_m=50_000.0,
                resolution_m=0.0,
            )

    def test_terrain_grid_plan_preserves_metadata(self):
        plan = TerrainGridPlan(
            target_crs="EPSG:32617",
            center_x_m=462000.0,
            center_y_m=3157000.0,
            west_m=412000.0,
            south_m=3106990.0,
            east_m=512020.0,
            north_m=3207010.0,
            resolution_m=30.0,
            width_px=3334,
            height_px=3334,
        )

        self.assertEqual(
            plan.width_px,
            3334,
        )

    def test_dem_tile_plan_preserves_metadata(self):
        tile = DemTilePlan(
            row=0,
            column=0,
            target_crs="EPSG:32617",
            west_m=400000.0,
            south_m=3100000.0,
            east_m=450010.0,
            north_m=3150010.0,
            resolution_m=30.0,
            width_px=1667,
            height_px=1667,
        )

        self.assertEqual(
            tile.width_px,
            1667,
        )

    def test_2x2_tile_plan_creates_four_tiles(self):
        grid = plan_terrain_grid(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
            resolution_m=30.0,
        )

        tiles = plan_dem_tiles(
            grid,
            rows=2,
            columns=2,
        )

        self.assertEqual(
            len(tiles),
            4,
        )

    def test_2x2_tile_dimensions_are_1667(self):
        grid = plan_terrain_grid(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
            resolution_m=30.0,
        )

        tiles = plan_dem_tiles(
            grid,
            rows=2,
            columns=2,
        )

        for tile in tiles:
            self.assertEqual(
                tile.width_px,
                1667,
            )

            self.assertEqual(
                tile.height_px,
                1667,
            )

    def test_tiles_cover_complete_grid(self):
        grid = plan_terrain_grid(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
            resolution_m=30.0,
        )

        tiles = plan_dem_tiles(
            grid,
            rows=2,
            columns=2,
        )

        total_pixels = sum(
            tile.width_px * tile.height_px
            for tile in tiles
        )

        self.assertEqual(
            total_pixels,
            grid.width_px * grid.height_px,
        )

    def test_tiles_align_with_grid_outer_bounds(self):
        grid = plan_terrain_grid(
            latitude=28.5383,
            longitude=-81.3792,
            radius_m=50_000.0,
            resolution_m=30.0,
        )

        tiles = plan_dem_tiles(
            grid,
            rows=2,
            columns=2,
        )

        self.assertAlmostEqual(
            min(tile.west_m for tile in tiles),
            grid.west_m,
        )

        self.assertAlmostEqual(
            max(tile.east_m for tile in tiles),
            grid.east_m,
        )

        self.assertAlmostEqual(
            min(tile.south_m for tile in tiles),
            grid.south_m,
        )

        self.assertAlmostEqual(
            max(tile.north_m for tile in tiles),
            grid.north_m,
        )

    def test_mosaic_dem_tiles_creates_expected_raster(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(
                temp_dir
            )

            grid = TerrainGridPlan(
                target_crs="EPSG:32617",
                center_x_m=60.0,
                center_y_m=60.0,
                west_m=0.0,
                south_m=0.0,
                east_m=120.0,
                north_m=120.0,
                resolution_m=30.0,
                width_px=4,
                height_px=4,
            )

            tiles = plan_dem_tiles(
                grid,
                rows=2,
                columns=2,
            )

            tile_files = {}

            for tile in tiles:
                file_path = (
                    temp_path
                    / f"tile_{tile.row}_{tile.column}.tif"
                )

                transform = from_origin(
                    tile.west_m,
                    tile.north_m,
                    tile.resolution_m,
                    tile.resolution_m,
                )

                value = float(
                    tile.row * 10
                    + tile.column
                    + 1
                )

                data = np.full(
                    (
                        tile.height_px,
                        tile.width_px,
                    ),
                    value,
                    dtype=np.float32,
                )

                with rasterio.open(
                    file_path,
                    "w",
                    driver="GTiff",
                    dtype="float32",
                    count=1,
                    crs=tile.target_crs,
                    transform=transform,
                    width=tile.width_px,
                    height=tile.height_px,
                ) as dst:
                    dst.write(
                        data,
                        1,
                    )

                tile_files[
                    (
                        tile.row,
                        tile.column,
                    )
                ] = str(
                    file_path
                )

            destination = (
                temp_path
                / "mosaic.tif"
            )

            result = mosaic_dem_tiles(
                grid=grid,
                tile_files=tile_files,
                destination_path=str(
                    destination
                ),
            )

            self.assertEqual(
                result.tile_count,
                4,
            )

            self.assertEqual(
                result.width_px,
                4,
            )

            self.assertEqual(
                result.height_px,
                4,
            )

            with rasterio.open(
                destination
            ) as src:
                self.assertEqual(
                    src.width,
                    4,
                )

                self.assertEqual(
                    src.height,
                    4,
                )

                self.assertEqual(
                    str(src.crs),
                    "EPSG:32617",
                )

                self.assertEqual(
                    src.nodata,
                    -9999.0,
                )

                data = src.read(
                    1
                )

                self.assertEqual(
                    float(data[0, 0]),
                    1.0,
                )

                self.assertEqual(
                    float(data[0, 3]),
                    2.0,
                )

                self.assertEqual(
                    float(data[3, 0]),
                    11.0,
                )

                self.assertEqual(
                    float(data[3, 3]),
                    12.0,
                )


if __name__ == "__main__":
    unittest.main()