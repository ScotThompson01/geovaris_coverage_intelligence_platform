import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin

from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
    sample_terrain_profile,
)


class TerrainProfileTests(unittest.TestCase):
    def _create_test_raster(
        self,
        directory: Path,
    ) -> Path:
        """Create a simple 10 x 10 projected DEM."""

        raster_path = (
            directory
            / "terrain.tif"
        )

        data = np.arange(
            100,
            dtype=np.float32,
        ).reshape(
            10,
            10,
        )

        transform = from_origin(
            500000.0,
            3200300.0,
            30.0,
            30.0,
        )

        with rasterio.open(
            raster_path,
            "w",
            driver="GTiff",
            dtype="float32",
            count=1,
            crs="EPSG:32617",
            transform=transform,
            width=10,
            height=10,
            nodata=-9999.0,
        ) as dataset:
            dataset.write(
                data,
                1,
            )

        return raster_path

    def _utm_to_wgs84(
        self,
        x_m: float,
        y_m: float,
    ) -> tuple[float, float]:
        transformer = Transformer.from_crs(
            "EPSG:32617",
            "EPSG:4326",
            always_xy=True,
        )

        longitude, latitude = transformer.transform(
            x_m,
            y_m,
        )

        return (
            latitude,
            longitude,
        )

    def test_profile_sample_preserves_metadata(self):
        sample = TerrainProfileSample(
            distance_m=30.0,
            latitude=28.0,
            longitude=-81.0,
            x_m=500000.0,
            y_m=3200000.0,
            elevation_m=42.5,
        )

        self.assertEqual(
            sample.distance_m,
            30.0,
        )

        self.assertEqual(
            sample.elevation_m,
            42.5,
        )

    def test_profile_preserves_metadata(self):
        sample = TerrainProfileSample(
            distance_m=0.0,
            latitude=28.0,
            longitude=-81.0,
            x_m=500000.0,
            y_m=3200000.0,
            elevation_m=10.0,
        )

        profile = TerrainProfile(
            raster_path="terrain.tif",
            raster_crs="EPSG:32617",
            total_distance_m=0.0,
            requested_spacing_m=30.0,
            actual_spacing_m=0.0,
            samples=(sample,),
        )

        self.assertEqual(
            profile.raster_crs,
            "EPSG:32617",
        )

        self.assertEqual(
            len(profile.samples),
            1,
        )

    def test_invalid_sample_spacing_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = self._create_test_raster(
                Path(temp_dir)
            )

            latitude, longitude = self._utm_to_wgs84(
                500015.0,
                3200285.0,
            )

            with self.assertRaises(ValueError):
                sample_terrain_profile(
                    raster_path=str(
                        raster_path
                    ),
                    start_latitude=latitude,
                    start_longitude=longitude,
                    end_latitude=latitude,
                    end_longitude=longitude,
                    sample_spacing_m=0.0,
                )

    def test_profile_samples_raster_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            raster_path = self._create_test_raster(
                Path(temp_dir)
            )

            start_latitude, start_longitude = (
                self._utm_to_wgs84(
                    500015.0,
                    3200285.0,
                )
            )

            end_latitude, end_longitude = (
                self._utm_to_wgs84(
                    500285.0,
                    3200015.0,
                )
            )

            profile = sample_terrain_profile(
                raster_path=str(
                    raster_path
                ),
                start_latitude=start_latitude,
                start_longitude=start_longitude,
                end_latitude=end_latitude,
                end_longitude=end_longitude,
                sample_spacing_m=30.0,
            )

            self.assertEqual(
                profile.raster_crs,
                "EPSG:32617",
            )

            self.assertGreater(
                profile.total_distance_m,
                0.0,
            )

            self.assertGreater(
                len(profile.samples),
                2,
            )

            self.assertEqual(
                profile.samples[0].elevation_m,
                0.0,
            )

            self.assertEqual(
                profile.samples[-1].elevation_m,
                99.0,
            )

            self.assertAlmostEqual(
                profile.samples[0].distance_m,
                0.0,
            )

            self.assertAlmostEqual(
                profile.samples[-1].distance_m,
                profile.total_distance_m,
            )

            self.assertLessEqual(
                profile.actual_spacing_m,
                30.0,
            )


if __name__ == "__main__":
    unittest.main()