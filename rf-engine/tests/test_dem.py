import unittest

from geovaris_rf.dem import (
    DemMetadata,
    GroundElevationResult,
    validate_coordinate,
)


class TestDem(unittest.TestCase):
    def test_valid_coordinate(self):
        validate_coordinate(28.5383, -81.3792)

    def test_invalid_latitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_coordinate(91.0, -81.3792)

    def test_invalid_longitude_rejected(self):
        with self.assertRaises(ValueError):
            validate_coordinate(28.5383, -181.0)

    def test_ground_elevation_result_preserves_metadata(self):
        metadata = DemMetadata(
            source="test_dem",
            version="test-1",
            horizontal_crs="EPSG:4326",
            vertical_datum="TEST_ONLY",
            units="meters",
            resolution_m=10.0,
        )

        result = GroundElevationResult(
            latitude=28.5383,
            longitude=-81.3792,
            elevation_m=25.0,
            metadata=metadata,
        )

        self.assertEqual(result.elevation_m, 25.0)
        self.assertEqual(result.metadata.source, "test_dem")
        self.assertEqual(result.metadata.version, "test-1")
        self.assertEqual(result.metadata.units, "meters")


if __name__ == "__main__":
    unittest.main()