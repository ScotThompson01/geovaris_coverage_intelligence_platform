import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

SRC_PATH = (
    PROJECT_ROOT
    / "src"
)

sys.path.insert(
    0,
    str(SRC_PATH),
)


from geovaris_rf.free_space import (  # noqa: E402
    FSPL_REFERENCE_DB,
    calculate_free_space_range,
    estimated_coverage_radius_m,
    free_space_path_loss_db,
    maximum_allowable_path_loss_db,
    maximum_free_space_distance_m,
    received_power_dbm,
    watts_to_dbm,
)


class FreeSpaceTests(
    unittest.TestCase
):
    def test_one_watt_equals_30_dbm(
        self,
    ):
        self.assertAlmostEqual(
            watts_to_dbm(
                1.0
            ),
            30.0,
            places=6,
        )

    def test_one_thousand_watts_equals_60_dbm(
        self,
    ):
        self.assertAlmostEqual(
            watts_to_dbm(
                1000.0
            ),
            60.0,
            places=6,
        )

    def test_invalid_power_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            watts_to_dbm(
                0.0
            )

    def test_non_finite_power_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            watts_to_dbm(
                math.inf
            )

    def test_fspl_600_mhz_at_one_km(
        self,
    ):
        result = (
            free_space_path_loss_db(
                frequency_mhz=600.0,
                distance_m=1000.0,
            )
        )

        expected = (
            FSPL_REFERENCE_DB
            + 20.0
            * math.log10(
                1.0
            )
            + 20.0
            * math.log10(
                600.0
            )
        )

        self.assertAlmostEqual(
            result,
            expected,
            places=6,
        )

    def test_received_power_without_extra_gain_or_losses(
        self,
    ):
        result = (
            received_power_dbm(
                frequency_mhz=600.0,
                distance_m=1000.0,
                eirp_watts=1000.0,
            )
        )

        path_loss = (
            free_space_path_loss_db(
                frequency_mhz=600.0,
                distance_m=1000.0,
            )
        )

        self.assertAlmostEqual(
            result,
            60.0 - path_loss,
            places=6,
        )

    def test_received_power_includes_receiver_gain_and_losses(
        self,
    ):
        result = (
            received_power_dbm(
                frequency_mhz=600.0,
                distance_m=1000.0,
                eirp_watts=1000.0,
                receiver_gain_dbi=6.0,
                additional_losses_db=2.0,
            )
        )

        path_loss = (
            free_space_path_loss_db(
                frequency_mhz=600.0,
                distance_m=1000.0,
            )
        )

        expected = (
            60.0
            + 6.0
            - path_loss
            - 2.0
        )

        self.assertAlmostEqual(
            result,
            expected,
            places=6,
        )

    def test_maximum_allowable_path_loss(
        self,
    ):
        result = (
            maximum_allowable_path_loss_db(
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                receiver_gain_dbi=3.0,
                additional_losses_db=2.0,
            )
        )

        self.assertAlmostEqual(
            result,
            156.0,
            places=6,
        )

    def test_calculated_distance_reaches_receiver_threshold(
        self,
    ):
        result = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
            )
        )

        path_loss = (
            free_space_path_loss_db(
                frequency_mhz=600.0,
                distance_m=(
                    result.maximum_distance_m
                ),
            )
        )

        received = (
            60.0
            - path_loss
        )

        self.assertAlmostEqual(
            received,
            -95.0,
            places=6,
        )

    def test_range_result_preserves_link_budget_inputs(
        self,
    ):
        result = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                receiver_gain_dbi=3.0,
                additional_losses_db=2.0,
            )
        )

        self.assertEqual(
            result.frequency_mhz,
            600.0,
        )

        self.assertEqual(
            result.eirp_dbm,
            60.0,
        )

        self.assertEqual(
            result.receiver_gain_dbi,
            3.0,
        )

        self.assertEqual(
            result.additional_losses_db,
            2.0,
        )

        self.assertEqual(
            result.receiver_threshold_dbm,
            -95.0,
        )

        self.assertEqual(
            result.maximum_path_loss_db,
            156.0,
        )

        self.assertGreater(
            result.maximum_distance_m,
            0.0,
        )

    def test_receiver_gain_increases_range(
        self,
    ):
        baseline = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                receiver_gain_dbi=0.0,
            )
        )

        with_gain = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                receiver_gain_dbi=6.0,
            )
        )

        self.assertGreater(
            with_gain.maximum_distance_m,
            baseline.maximum_distance_m,
        )

    def test_additional_losses_reduce_range(
        self,
    ):
        baseline = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                additional_losses_db=0.0,
            )
        )

        with_losses = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                additional_losses_db=10.0,
            )
        )

        self.assertLess(
            with_losses.maximum_distance_m,
            baseline.maximum_distance_m,
        )

    def test_invalid_additional_losses_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
                additional_losses_db=-1.0,
            )

    def test_maximum_free_space_distance_watts_api_remains_supported(
        self,
    ):
        result = (
            maximum_free_space_distance_m(
                frequency_mhz=600.0,
                eirp_watts=1000.0,
                receiver_threshold_dbm=-95.0,
            )
        )

        direct = (
            calculate_free_space_range(
                frequency_mhz=600.0,
                eirp_dbm=60.0,
                receiver_threshold_dbm=-95.0,
            )
        )

        self.assertAlmostEqual(
            result,
            direct.maximum_distance_m,
            places=6,
        )

    def test_calculation_radius_limits_output(
        self,
    ):
        result = (
            estimated_coverage_radius_m(
                frequency_mhz=600.0,
                eirp_watts=1000.0,
                receiver_threshold_dbm=-95.0,
                calculation_radius_m=50000.0,
            )
        )

        self.assertLessEqual(
            result,
            50000.0,
        )


if __name__ == "__main__":
    unittest.main()