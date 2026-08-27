import unittest

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)
from geovaris_rf.clutter_loss import (
    ClutterLossModel,
    ClutterLossRequest,
    ClutterLossResult,
)


class TestClutterLossModel(
    ClutterLossModel
):
    @property
    def model_name(
        self,
    ) -> str:
        return "Test Clutter Model"

    @property
    def model_version(
        self,
    ) -> str:
        return "test-1.0"

    def calculate(
        self,
        request: ClutterLossRequest,
    ) -> ClutterLossResult:
        return ClutterLossResult(
            model_name=self.model_name,
            model_version=self.model_version,
            clutter_loss_db=5.0,
            assumptions={
                "clutter_class":
                    request.clutter_class.value,
            },
        )


class ClutterLossContractTests(
    unittest.TestCase
):
    def _valid_request(
        self,
    ) -> ClutterLossRequest:
        return ClutterLossRequest(
            frequency_mhz=600.0,
            clutter_class=(
                GeoVarisClutterClass.SUBURBAN
            ),
            path_distance_m=1000.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
        )

    def test_valid_request(
        self,
    ):
        request = (
            self._valid_request()
        )

        self.assertEqual(
            request.frequency_mhz,
            600.0,
        )

        self.assertEqual(
            request.clutter_class,
            GeoVarisClutterClass.SUBURBAN,
        )

    def test_invalid_frequency_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            ClutterLossRequest(
                frequency_mhz=0.0,
                clutter_class=(
                    GeoVarisClutterClass.SUBURBAN
                ),
                path_distance_m=1000.0,
                transmitter_height_agl_m=45.72,
                receiver_height_agl_m=2.0,
            )

    def test_negative_path_distance_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            ClutterLossRequest(
                frequency_mhz=600.0,
                clutter_class=(
                    GeoVarisClutterClass.SUBURBAN
                ),
                path_distance_m=-1.0,
                transmitter_height_agl_m=45.72,
                receiver_height_agl_m=2.0,
            )

    def test_invalid_clutter_class_is_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            ClutterLossRequest(
                frequency_mhz=600.0,
                clutter_class="suburban",  # type: ignore[arg-type]
                path_distance_m=1000.0,
                transmitter_height_agl_m=45.72,
                receiver_height_agl_m=2.0,
            )

    def test_result_allows_negative_statistical_loss(
        self,
    ):
        result = ClutterLossResult(
            model_name="Test",
            model_version="1.0",
            clutter_loss_db=-0.5,
        )

        self.assertEqual(
            result.clutter_loss_db,
            -0.5,
        )

    def test_result_rejects_nonfinite_loss(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            ClutterLossResult(
                model_name="Test",
                model_version="1.0",
                clutter_loss_db=float(
                    "nan"
                ),
            )
    def test_model_returns_typed_result(
        self,
    ):
        model = (
            TestClutterLossModel()
        )

        result = model.calculate(
            self._valid_request()
        )

        self.assertEqual(
            result.model_name,
            "Test Clutter Model",
        )

        self.assertEqual(
            result.model_version,
            "test-1.0",
        )

        self.assertEqual(
            result.clutter_loss_db,
            5.0,
        )

        self.assertEqual(
            result.assumptions[
                "clutter_class"
            ],
            "suburban",
        )


if __name__ == "__main__":
    unittest.main()