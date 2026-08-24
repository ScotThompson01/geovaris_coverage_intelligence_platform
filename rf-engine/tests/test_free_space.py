import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))


from geovaris_rf.free_space import (  # noqa: E402
    estimated_coverage_radius_m,
    free_space_path_loss_db,
    received_power_dbm,
    watts_to_dbm,
)


class FreeSpaceTests(unittest.TestCase):
    def test_one_watt_equals_30_dbm(self):
        self.assertAlmostEqual(
            watts_to_dbm(1.0),
            30.0,
            places=6,
        )

    def test_one_thousand_watts_equals_60_dbm(self):
        self.assertAlmostEqual(
            watts_to_dbm(1000.0),
            60.0,
            places=6,
        )

    def test_fspl_600_mhz_at_one_km(self):
        result = free_space_path_loss_db(
            frequency_mhz=600.0,
            distance_m=1000.0,
        )

        expected = (
            32.44
            + 20.0 * math.log10(1.0)
            + 20.0 * math.log10(600.0)
        )

        self.assertAlmostEqual(
            result,
            expected,
            places=6,
        )

    def test_received_power(self):
        result = received_power_dbm(
            frequency_mhz=600.0,
            distance_m=1000.0,
            eirp_watts=1000.0,
        )

        path_loss = free_space_path_loss_db(
            frequency_mhz=600.0,
            distance_m=1000.0,
        )

        self.assertAlmostEqual(
            result,
            60.0 - path_loss,
            places=6,
        )

    def test_calculation_radius_limits_output(self):
        result = estimated_coverage_radius_m(
            frequency_mhz=600.0,
            eirp_watts=1000.0,
            receiver_threshold_dbm=-95.0,
            calculation_radius_m=50000.0,
        )

        self.assertLessEqual(
            result,
            50000.0,
        )

    def test_invalid_power_rejected(self):
        with self.assertRaises(ValueError):
            watts_to_dbm(0.0)


if __name__ == "__main__":
    unittest.main()