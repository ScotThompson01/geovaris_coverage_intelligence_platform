import unittest
from pathlib import Path
from unittest.mock import patch

from geovaris_rf.itm import (
    ItmClimate,
    ItmConfiguration,
    ItmPolarization,
    ItmVariabilityMode,
)
from geovaris_rf.itm_model import (
    ItmModel,
    decode_itm_warning_flags,
)
from geovaris_rf.itm_native import (
    ItmIntermediateValues,
    ItmNativeResult,
)
from geovaris_rf.propagation import (
    PropagationRequest,
    PropagationResult,
)
from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
)


class ItmModelTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(
        cls,
    ) -> None:
        rf_engine_root = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

        cls.dll_path = (
            rf_engine_root
            / "vendor"
            / "ntia-itm"
            / "itm.dll"
        )

    def _make_configuration(
        self,
    ) -> ItmConfiguration:
        return ItmConfiguration(
            climate=(
                ItmClimate.CONTINENTAL_TEMPERATE
            ),
            polarization=(
                ItmPolarization.VERTICAL
            ),
            variability_mode=(
                ItmVariabilityMode.BROADCAST
            ),
            surface_refractivity_n_units=301.0,
            ground_dielectric_constant=15.0,
            ground_conductivity_s_per_m=0.005,
            confidence=0.50,
            reliability=0.50,
        )

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

    def test_model_name_and_version(
        self,
    ):
        if not self.dll_path.exists():
            self.skipTest(
                "NTIA itm.dll not installed locally."
            )

        model = ItmModel(
            dll_path=str(
                self.dll_path
            ),
            configuration=(
                self._make_configuration()
            ),
        )

        self.assertEqual(
            model.model_name,
            "NTIA ITM",
        )

        self.assertEqual(
            model.model_version,
            "1.4",
        )

    def test_model_returns_propagation_result(
        self,
    ):
        if not self.dll_path.exists():
            self.skipTest(
                "NTIA itm.dll not installed locally."
            )

        model = ItmModel(
            dll_path=str(
                self.dll_path
            ),
            configuration=(
                self._make_configuration()
            ),
        )

        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=(
                self._make_profile()
            ),
        )

        result = model.calculate(
            request
        )

        self.assertIsInstance(
            result,
            PropagationResult,
        )

        self.assertEqual(
            result.model_name,
            "NTIA ITM",
        )

        self.assertEqual(
            result.model_version,
            "1.4",
        )

        self.assertGreater(
            result.basic_transmission_loss_db,
            0.0,
        )

        self.assertIn(
            result.propagation_mode,
            (
                "line_of_sight",
                "diffraction",
                "troposcatter",
            ),
        )

    def test_model_preserves_assumptions(
        self,
    ):
        if not self.dll_path.exists():
            self.skipTest(
                "NTIA itm.dll not installed locally."
            )

        configuration = (
            self._make_configuration()
        )

        model = ItmModel(
            dll_path=str(
                self.dll_path
            ),
            configuration=(
                configuration
            ),
        )

        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=(
                self._make_profile()
            ),
        )

        result = model.calculate(
            request
        )

        self.assertEqual(
            result.assumptions[
                "climate"
            ],
            5,
        )

        self.assertEqual(
            result.assumptions[
                "polarization"
            ],
            1,
        )

        self.assertEqual(
            result.assumptions[
                "variability_mode"
            ],
            3,
        )

        self.assertEqual(
            result.assumptions[
                "confidence"
            ],
            0.50,
        )

        self.assertEqual(
            result.assumptions[
                "reliability"
            ],
            0.50,
        )

    def test_zero_warning_flags_decode_empty(
        self,
    ):
        self.assertEqual(
            decode_itm_warning_flags(
                0x0000
            ),
            (),
        )

    def test_short_path_warning_decodes(
        self,
    ):
        self.assertEqual(
            decode_itm_warning_flags(
                0x0040
            ),
            (
                "WARN__PATH_DISTANCE_TOO_SMALL_2",
            ),
        )

    def test_rx_horizon_warning_decodes(
        self,
    ):
        self.assertEqual(
            decode_itm_warning_flags(
                0x0400
            ),
            (
                "WARN__RX_HORIZON_DISTANCE_1",
            ),
        )

    def test_combined_warning_flags_decode(
        self,
    ):
        self.assertEqual(
            decode_itm_warning_flags(
                0x0600
            ),
            (
                "WARN__TX_HORIZON_DISTANCE_1",
                "WARN__RX_HORIZON_DISTANCE_1",
            ),
        )

    def test_unknown_warning_bits_are_preserved(
        self,
    ):
        self.assertEqual(
            decode_itm_warning_flags(
                0x8000
            ),
            (
                "UNKNOWN_ITM_WARNING_BITS_0x8000",
            ),
        )

    def test_negative_warning_flags_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            decode_itm_warning_flags(
                -1
            )

    def test_success_with_warnings_is_not_fatal(
        self,
    ):
        if not self.dll_path.exists():
            self.skipTest(
                "NTIA itm.dll not installed locally."
            )

        model = ItmModel(
            dll_path=str(
                self.dll_path
            ),
            configuration=(
                self._make_configuration()
            ),
        )

        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=(
                self._make_profile()
            ),
        )

        warning_result = ItmNativeResult(
            return_code=1,
            warning_flags=0x0600,
            basic_transmission_loss_db=100.0,
            intermediate=(
                ItmIntermediateValues(
                    theta_hzn_tx_rad=0.0,
                    theta_hzn_rx_rad=0.0,
                    distance_horizon_tx_m=1000.0,
                    distance_horizon_rx_m=1000.0,
                    effective_height_tx_m=45.72,
                    effective_height_rx_m=2.0,
                    surface_refractivity_n_units=300.0,
                    terrain_irregularity_m=5.0,
                    reference_attenuation_db=1.0,
                    free_space_loss_db=99.0,
                    path_distance_km=1.0,
                    propagation_mode=1,
                )
            ),
        )

        with patch.object(
            model._native_library,
            "calculate_p2p_cr",
            return_value=warning_result,
        ):
            result = model.calculate(
                request
            )

        self.assertEqual(
            result.basic_transmission_loss_db,
            100.0,
        )

        self.assertEqual(
            result.assumptions[
                "itm_return_code"
            ],
            1,
        )

        self.assertEqual(
            result.assumptions[
                "itm_warning_flags"
            ],
            0x0600,
        )

        self.assertEqual(
            result.warnings,
            (
                "WARN__TX_HORIZON_DISTANCE_1",
                "WARN__RX_HORIZON_DISTANCE_1",
            ),
        )

        self.assertEqual(
            result.assumptions[
                "itm_warning_names"
            ],
            (
                "WARN__TX_HORIZON_DISTANCE_1",
                "WARN__RX_HORIZON_DISTANCE_1",
            ),
        )

        self.assertEqual(
            result.propagation_mode,
            "line_of_sight",
        )


if __name__ == "__main__":
    unittest.main()