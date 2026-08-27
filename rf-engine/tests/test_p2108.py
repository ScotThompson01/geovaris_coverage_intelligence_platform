import unittest

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)
from geovaris_rf.clutter_loss import (
    ClutterLossRequest,
)
from geovaris_rf.p2108 import (
    P2108TerrestrialClutterModel,
)


class P2108TerrestrialClutterTests(
    unittest.TestCase
):
    def _request(
        self,
        *,
        frequency_mhz: float = 3000.0,
        path_distance_m: float = 500.0,
        clutter_class=(
            GeoVarisClutterClass.SUBURBAN
        ),
        transmitter_height_agl_m: float = 45.72,
        receiver_height_agl_m: float = 2.0,
        percentage_locations: float = 50.0,
        correction_end: str = "receiver",
    ) -> ClutterLossRequest:
        return ClutterLossRequest(
            frequency_mhz=frequency_mhz,
            clutter_class=clutter_class,
            path_distance_m=(
                path_distance_m
            ),
            transmitter_height_agl_m=(
                transmitter_height_agl_m
            ),
            receiver_height_agl_m=(
                receiver_height_agl_m
            ),
            model_parameters={
                "percentage_locations":
                    percentage_locations,
                "correction_end":
                    correction_end,
            },
        )

    def test_p2108_1_reference_equation_value(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        result = model.calculate(
            self._request()
        )

        self.assertAlmostEqual(
            result.clutter_loss_db,
            26.628119499528943,
            places=10,
        )

    def test_loss_is_capped_at_two_km(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        result_2km = model.calculate(
            self._request(
                path_distance_m=2000.0
            )
        )

        result_10km = model.calculate(
            self._request(
                path_distance_m=10000.0
            )
        )

        self.assertAlmostEqual(
            result_10km.clutter_loss_db,
            result_2km.clutter_loss_db,
            places=12,
        )

        self.assertTrue(
            result_10km.assumptions[
                "capped_to_2km"
            ]
        )

    def test_one_end_allows_250_m_path(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        result = model.calculate(
            self._request(
                path_distance_m=250.0,
                correction_end="receiver",
            )
        )

        self.assertIsInstance(
            result.clutter_loss_db,
            float,
        )

    def test_one_end_rejects_path_below_250_m(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        with self.assertRaises(
            ValueError
        ):
            model.calculate(
                self._request(
                    path_distance_m=249.0,
                    correction_end="receiver",
                )
            )

    def test_both_ends_require_one_km(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        with self.assertRaises(
            ValueError
        ):
            model.calculate(
                self._request(
                    path_distance_m=999.0,
                    correction_end="both",
                )
            )

    def test_frequency_outside_model_range_is_rejected(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        for frequency_mhz in (
            499.0,
            67001.0,
        ):
            with self.subTest(
                frequency_mhz=frequency_mhz
            ):
                with self.assertRaises(
                    ValueError
                ):
                    model.calculate(
                        self._request(
                            frequency_mhz=(
                                frequency_mhz
                            )
                        )
                    )

    def test_percentage_locations_is_required(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        request = self._request()

        request = ClutterLossRequest(
            frequency_mhz=(
                request.frequency_mhz
            ),
            clutter_class=(
                request.clutter_class
            ),
            path_distance_m=(
                request.path_distance_m
            ),
            transmitter_height_agl_m=(
                request.transmitter_height_agl_m
            ),
            receiver_height_agl_m=(
                request.receiver_height_agl_m
            ),
            model_parameters={
                "correction_end":
                    "receiver",
            },
        )

        with self.assertRaises(
            ValueError
        ):
            model.calculate(
                request
            )

    def test_invalid_percentage_locations_is_rejected(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        for percentage in (
            0.0,
            100.0,
        ):
            with self.subTest(
                percentage=percentage
            ):
                with self.assertRaises(
                    ValueError
                ):
                    model.calculate(
                        self._request(
                            percentage_locations=(
                                percentage
                            )
                        )
                    )

    def test_correction_end_is_required(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        request = self._request()

        request = ClutterLossRequest(
            frequency_mhz=(
                request.frequency_mhz
            ),
            clutter_class=(
                request.clutter_class
            ),
            path_distance_m=(
                request.path_distance_m
            ),
            transmitter_height_agl_m=(
                request.transmitter_height_agl_m
            ),
            receiver_height_agl_m=(
                request.receiver_height_agl_m
            ),
            model_parameters={
                "percentage_locations":
                    50.0,
            },
        )

        with self.assertRaises(
            ValueError
        ):
            model.calculate(
                request
            )

    def test_non_urban_clutter_is_rejected(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        with self.assertRaises(
            ValueError
        ):
            model.calculate(
                self._request(
                    clutter_class=(
                        GeoVarisClutterClass.FOREST
                    )
                )
            )

    def test_receiver_height_above_measurement_range_warns(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        result = model.calculate(
            self._request(
                receiver_height_agl_m=10.0,
                correction_end="receiver",
            )
        )

        self.assertEqual(
            len(
                result.warnings
            ),
            1,
        )

        self.assertIn(
            "Receiver",
            result.warnings[0],
        )

    def test_low_statistical_tail_can_be_negative(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        result = model.calculate(
            self._request(
                frequency_mhz=500.0,
                path_distance_m=250.0,
                percentage_locations=0.1,
                correction_end="receiver",
            )
        )

        self.assertLess(
            result.clutter_loss_db,
            0.0,
        )

    def test_result_preserves_model_lineage(
        self,
    ):
        model = (
            P2108TerrestrialClutterModel()
        )

        result = model.calculate(
            self._request(
                clutter_class=(
                    GeoVarisClutterClass.DENSE_SUBURBAN
                )
            )
        )

        self.assertEqual(
            result.model_name,
            (
                "ITU-R P.2108 Terrestrial "
                "Statistical Clutter"
            ),
        )

        self.assertEqual(
            result.model_version,
            "P.2108-1 (09/2021) §3.2",
        )

        self.assertEqual(
            result.assumptions[
                "percentage_locations"
            ],
            50.0,
        )

        self.assertEqual(
            result.assumptions[
                "correction_end"
            ],
            "receiver",
        )

        self.assertEqual(
            result.assumptions[
                "clutter_class"
            ],
            "dense_suburban",
        )


if __name__ == "__main__":
    unittest.main()