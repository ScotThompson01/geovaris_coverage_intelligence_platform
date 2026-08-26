import unittest

from geovaris_rf.propagation import (
    PropagationModel,
    PropagationRequest,
    PropagationResult,
)
from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
)


class DummyPropagationModel(
    PropagationModel
):
    """Simple test implementation of the model interface."""

    @property
    def model_name(self) -> str:
        return "Dummy"

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
            basic_transmission_loss_db=100.0,
            propagation_mode="test",
            assumptions={
                "frequency_mhz": (
                    request.frequency_mhz
                ),
            },
        )


class PropagationTests(
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
            requested_spacing_m=30.0,
            actual_spacing_m=30.0,
            samples=samples,
        )

    def test_valid_request(self):
        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        self.assertEqual(
            request.frequency_mhz,
            600.0,
        )

        self.assertEqual(
            request.transmitter_height_agl_m,
            45.72,
        )

    def test_6000_mhz_is_supported(self):
        request = PropagationRequest(
            frequency_mhz=6000.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        self.assertEqual(
            request.frequency_mhz,
            6000.0,
        )

    def test_frequency_below_supported_range_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationRequest(
                frequency_mhz=599.0,
                transmitter_height_agl_m=30.0,
                receiver_height_agl_m=2.0,
                terrain_profile=self._make_profile(),
            )

    def test_frequency_above_supported_range_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationRequest(
                frequency_mhz=6001.0,
                transmitter_height_agl_m=30.0,
                receiver_height_agl_m=2.0,
                terrain_profile=self._make_profile(),
            )

    def test_negative_tx_height_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationRequest(
                frequency_mhz=900.0,
                transmitter_height_agl_m=-1.0,
                receiver_height_agl_m=2.0,
                terrain_profile=self._make_profile(),
            )

    def test_negative_rx_height_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationRequest(
                frequency_mhz=900.0,
                transmitter_height_agl_m=30.0,
                receiver_height_agl_m=-1.0,
                terrain_profile=self._make_profile(),
            )

    def test_model_parameters_preserved(self):
        request = PropagationRequest(
            frequency_mhz=900.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
            model_parameters={
                "example": 123,
            },
        )

        self.assertEqual(
            request.model_parameters[
                "example"
            ],
            123,
        )

    def test_result_preserves_model_lineage(self):
        result = PropagationResult(
            model_name="NTIA ITM",
            model_version="test-version",
            basic_transmission_loss_db=135.5,
            propagation_mode="diffraction",
        )

        self.assertEqual(
            result.model_name,
            "NTIA ITM",
        )

        self.assertEqual(
            result.model_version,
            "test-version",
        )

        self.assertEqual(
            result.basic_transmission_loss_db,
            135.5,
        )

    def test_negative_loss_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationResult(
                model_name="Test",
                model_version="1",
                basic_transmission_loss_db=-1.0,
            )

    def test_empty_model_name_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationResult(
                model_name="",
                model_version="1",
                basic_transmission_loss_db=100.0,
            )

    def test_empty_model_version_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            PropagationResult(
                model_name="Test",
                model_version="",
                basic_transmission_loss_db=100.0,
            )

    def test_dummy_model_implements_interface(self):
        model = DummyPropagationModel()

        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        result = model.calculate(
            request
        )

        self.assertIsInstance(
            model,
            PropagationModel,
        )

        self.assertEqual(
            result.model_name,
            "Dummy",
        )

        self.assertEqual(
            result.model_version,
            "1.0",
        )

        self.assertEqual(
            result.basic_transmission_loss_db,
            100.0,
        )

    def test_result_warnings_preserved(self):
        result = PropagationResult(
            model_name="Test",
            model_version="1",
            basic_transmission_loss_db=100.0,
            warnings=(
                "Example engineering warning",
            ),
        )

        self.assertEqual(
            len(result.warnings),
            1,
        )

    def test_result_assumptions_preserved(self):
        result = PropagationResult(
            model_name="Test",
            model_version="1",
            basic_transmission_loss_db=100.0,
            assumptions={
                "climate": 5,
                "polarization": "vertical",
            },
        )

        self.assertEqual(
            result.assumptions[
                "climate"
            ],
            5,
        )


if __name__ == "__main__":
    unittest.main()