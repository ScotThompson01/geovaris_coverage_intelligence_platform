import unittest

from geovaris_rf.path_evaluation import (
    PathEvaluationRequest,
    PathEvaluationResult,
    evaluate_path,
)
from geovaris_rf.propagation import (
    PropagationModel,
    PropagationRequest,
    PropagationResult,
)
from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
)
from geovaris_rf.clutter_loss import (
    ClutterLossResult,
)

class DummyPropagationModel(
    PropagationModel
):
    @property
    def model_name(self) -> str:
        return "Dummy Model"

    @property
    def model_version(self) -> str:
        return "1.0"

    def calculate(
        self,
        request: PropagationRequest,
    ) -> PropagationResult:
        return PropagationResult(
            model_name=self.model_name,
            model_version=self.model_version,
            basic_transmission_loss_db=120.0,
            propagation_mode="test",
            warnings=(),
            assumptions={
                "frequency_mhz": (
                    request.frequency_mhz
                )
            },
        )


class PathEvaluationTests(
    unittest.TestCase
):
    def _make_profile(
        self,
    ) -> TerrainProfile:
        samples = (
            TerrainProfileSample(
                distance_m=0.0,
                latitude=28.0,
                longitude=-81.0,
                x_m=500000.0,
                y_m=3200000.0,
                elevation_m=30.0,
            ),
            TerrainProfileSample(
                distance_m=1000.0,
                latitude=28.0,
                longitude=-80.99,
                x_m=501000.0,
                y_m=3200000.0,
                elevation_m=35.0,
            ),
        )

        return TerrainProfile(
            raster_path="terrain.tif",
            raster_crs="EPSG:32617",
            total_distance_m=1000.0,
            requested_spacing_m=1000.0,
            actual_spacing_m=1000.0,
            samples=samples,
        )

    def _make_propagation_request(
        self,
    ) -> PropagationRequest:
        return PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=(
                self._make_profile()
            ),
        )

    def test_evaluate_path_returns_result(
        self,
    ):
        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            receiver_threshold_dbm=-90.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertIsInstance(
            result,
            PathEvaluationResult,
        )

    def test_propagation_result_is_preserved(
        self,
    ):
        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            receiver_threshold_dbm=-90.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.model_name,
            "Dummy Model",
        )

        self.assertEqual(
            result.model_version,
            "1.0",
        )

        self.assertEqual(
            result.propagation_loss_db,
            120.0,
        )

    def test_link_budget_result_is_preserved(
        self,
    ):
        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            receiver_gain_dbi=5.0,
            additional_losses_db=3.0,
            receiver_threshold_dbm=-70.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.predicted_received_power_dbm,
            -58.0,
        )

        self.assertEqual(
            result.receiver_threshold_dbm,
            -70.0,
        )

        self.assertEqual(
            result.margin_db,
            12.0,
        )

        self.assertTrue(
            result.meets_threshold,
        )

    def test_threshold_failure_is_preserved(
        self,
    ):
        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=30.0,
            receiver_threshold_dbm=-80.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.predicted_received_power_dbm,
            -90.0,
        )

        self.assertEqual(
            result.margin_db,
            -10.0,
        )

        self.assertFalse(
            result.meets_threshold,
        )

    def test_propagation_assumptions_remain_available(
        self,
    ):
        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.propagation.assumptions[
                "frequency_mhz"
            ],
            600.0,
        )
    def test_without_clutter_preserves_existing_loss_semantics(
        self,
    ):
        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            receiver_threshold_dbm=-90.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.propagation_loss_db,
            120.0,
        )

        self.assertEqual(
            result.terrain_loss_db,
            120.0,
        )

        self.assertIsNone(
            result.clutter_loss_db
        )

        self.assertEqual(
            result.total_path_loss_db,
            120.0,
        )

    def test_clutter_loss_is_added_to_total_path_loss(
        self,
    ):
        clutter_loss = (
            ClutterLossResult(
                model_name=(
                    "ITU-R P.2108 Terrestrial "
                    "Statistical Clutter"
                ),
                model_version=(
                    "P.2108-1 (09/2021) §3.2"
                ),
                clutter_loss_db=20.0,
                assumptions={
                    "correction_end":
                        "receiver",
                },
            )
        )

        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            clutter_loss=clutter_loss,
            receiver_threshold_dbm=-90.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.terrain_loss_db,
            120.0,
        )

        self.assertEqual(
            result.clutter_loss_db,
            20.0,
        )

        self.assertEqual(
            result.total_path_loss_db,
            140.0,
        )

    def test_clutter_loss_affects_received_power(
        self,
    ):
        clutter_loss = (
            ClutterLossResult(
                model_name="Test Clutter",
                model_version="1.0",
                clutter_loss_db=20.0,
            )
        )

        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            clutter_loss=clutter_loss,
            receiver_threshold_dbm=-90.0,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.predicted_received_power_dbm,
            -80.0,
        )

        self.assertEqual(
            result.margin_db,
            10.0,
        )

        self.assertTrue(
            result.meets_threshold,
        )

    def test_clutter_lineage_is_preserved(
        self,
    ):
        clutter_loss = (
            ClutterLossResult(
                model_name="Test Clutter",
                model_version="2.0",
                clutter_loss_db=10.0,
                assumptions={
                    "clutter_class":
                        "dense_suburban",
                },
            )
        )

        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            clutter_loss=clutter_loss,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertIs(
            result.clutter_loss,
            clutter_loss,
        )

        self.assertEqual(
            result.clutter_loss.model_name,
            "Test Clutter",
        )

        self.assertEqual(
            result.clutter_loss.assumptions[
                "clutter_class"
            ],
            "dense_suburban",
        )

    def test_negative_statistical_clutter_correction_is_preserved(
        self,
    ):
        clutter_loss = (
            ClutterLossResult(
                model_name="Statistical Clutter",
                model_version="1.0",
                clutter_loss_db=-0.5,
            )
        )

        request = PathEvaluationRequest(
            propagation_request=(
                self._make_propagation_request()
            ),
            eirp_dbm=60.0,
            clutter_loss=clutter_loss,
        )

        result = evaluate_path(
            DummyPropagationModel(),
            request,
        )

        self.assertEqual(
            result.terrain_loss_db,
            120.0,
        )

        self.assertEqual(
            result.clutter_loss_db,
            -0.5,
        )

        self.assertEqual(
            result.total_path_loss_db,
            119.5,
        )

if __name__ == "__main__":
    unittest.main()