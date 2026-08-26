import math
import unittest

from geovaris_rf.link_budget import (
    LinkBudgetRequest,
    LinkBudgetResult,
    calculate_received_power_dbm,
    evaluate_link_budget,
)


class LinkBudgetTests(
    unittest.TestCase
):
    def test_received_power_basic(self):
        result = (
            calculate_received_power_dbm(
                eirp_dbm=60.0,
                propagation_loss_db=120.0,
            )
        )

        self.assertEqual(
            result,
            -60.0,
        )

    def test_receiver_gain_is_added(self):
        result = (
            calculate_received_power_dbm(
                eirp_dbm=60.0,
                propagation_loss_db=120.0,
                receiver_gain_dbi=5.0,
            )
        )

        self.assertEqual(
            result,
            -55.0,
        )

    def test_additional_losses_are_subtracted(self):
        result = (
            calculate_received_power_dbm(
                eirp_dbm=60.0,
                propagation_loss_db=120.0,
                additional_losses_db=3.0,
            )
        )

        self.assertEqual(
            result,
            -63.0,
        )

    def test_link_budget_meets_threshold(self):
        request = LinkBudgetRequest(
            eirp_dbm=60.0,
            propagation_loss_db=120.0,
            receiver_gain_dbi=0.0,
            additional_losses_db=0.0,
            receiver_threshold_dbm=-70.0,
        )

        result = evaluate_link_budget(
            request
        )

        self.assertIsInstance(
            result,
            LinkBudgetResult,
        )

        self.assertEqual(
            result.predicted_received_power_dbm,
            -60.0,
        )

        self.assertEqual(
            result.margin_db,
            10.0,
        )

        self.assertTrue(
            result.meets_threshold
        )

    def test_link_budget_fails_threshold(self):
        request = LinkBudgetRequest(
            eirp_dbm=60.0,
            propagation_loss_db=140.0,
            receiver_threshold_dbm=-75.0,
        )

        result = evaluate_link_budget(
            request
        )

        self.assertEqual(
            result.predicted_received_power_dbm,
            -80.0,
        )

        self.assertEqual(
            result.margin_db,
            -5.0,
        )

        self.assertFalse(
            result.meets_threshold
        )

    def test_exact_threshold_counts_as_meeting(self):
        request = LinkBudgetRequest(
            eirp_dbm=60.0,
            propagation_loss_db=140.0,
            receiver_threshold_dbm=-80.0,
        )

        result = evaluate_link_budget(
            request
        )

        self.assertEqual(
            result.margin_db,
            0.0,
        )

        self.assertTrue(
            result.meets_threshold
        )

    def test_negative_propagation_loss_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            LinkBudgetRequest(
                eirp_dbm=60.0,
                propagation_loss_db=-1.0,
            )

    def test_negative_additional_loss_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            LinkBudgetRequest(
                eirp_dbm=60.0,
                propagation_loss_db=120.0,
                additional_losses_db=-1.0,
            )

    def test_nonfinite_value_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            LinkBudgetRequest(
                eirp_dbm=math.inf,
                propagation_loss_db=120.0,
            )

    def test_function_rejects_negative_loss(self):
        with self.assertRaises(
            ValueError
        ):
            calculate_received_power_dbm(
                eirp_dbm=60.0,
                propagation_loss_db=-1.0,
            )


if __name__ == "__main__":
    unittest.main()