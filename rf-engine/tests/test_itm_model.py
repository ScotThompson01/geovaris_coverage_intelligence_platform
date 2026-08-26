import unittest
from pathlib import Path

from geovaris_rf.itm import (
    ItmClimate,
    ItmConfiguration,
    ItmPolarization,
    ItmVariabilityMode,
)
from geovaris_rf.itm_model import (
    ItmModel,
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


if __name__ == "__main__":
    unittest.main()