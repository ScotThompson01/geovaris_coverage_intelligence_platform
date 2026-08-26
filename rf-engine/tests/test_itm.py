import unittest

from geovaris_rf.itm import (
    ItmClimate,
    ItmConfiguration,
    ItmNativeInput,
    ItmPolarization,
    ItmPreparedRequest,
    ItmTerrainProfile,
    ItmVariabilityMode,
    prepare_itm_request,
    terrain_profile_to_itm,
)
from geovaris_rf.propagation import (
    PropagationRequest,
)
from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
)


class ItmTests(
    unittest.TestCase
):
    def _make_profile(
        self,
        spacing_m: float = 30.0,
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
                distance_m=spacing_m,
                latitude=28.0,
                longitude=-80.9997,
                x_m=500030.0,
                y_m=3200000.0,
                elevation_m=35.0,
            ),
            TerrainProfileSample(
                distance_m=spacing_m * 2.0,
                latitude=28.0,
                longitude=-80.9994,
                x_m=500060.0,
                y_m=3200000.0,
                elevation_m=33.0,
            ),
        )

        return TerrainProfile(
            raster_path="terrain.tif",
            raster_crs="EPSG:32617",
            total_distance_m=(
                spacing_m * 2.0
            ),
            requested_spacing_m=spacing_m,
            actual_spacing_m=spacing_m,
            samples=samples,
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

    def test_climate_enum_values(self):
        self.assertEqual(
            int(
                ItmClimate.CONTINENTAL_TEMPERATE
            ),
            5,
        )

    def test_polarization_enum_values(self):
        self.assertEqual(
            int(
                ItmPolarization.HORIZONTAL
            ),
            0,
        )

        self.assertEqual(
            int(
                ItmPolarization.VERTICAL
            ),
            1,
        )

    def test_variability_mode_values(self):
        self.assertEqual(
            int(
                ItmVariabilityMode.SINGLE_MESSAGE
            ),
            0,
        )

        self.assertEqual(
            int(
                ItmVariabilityMode.BROADCAST
            ),
            3,
        )

    def test_valid_configuration(self):
        configuration = (
            self._make_configuration()
        )

        self.assertEqual(
            configuration.variability_mode,
            ItmVariabilityMode.BROADCAST,
        )

    def test_refractivity_below_ntia_range_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            ItmConfiguration(
                climate=ItmClimate.CONTINENTAL_TEMPERATE,
                polarization=ItmPolarization.VERTICAL,
                variability_mode=ItmVariabilityMode.BROADCAST,
                surface_refractivity_n_units=249.0,
                ground_dielectric_constant=15.0,
                ground_conductivity_s_per_m=0.005,
                confidence=0.50,
                reliability=0.50,
            )

    def test_refractivity_above_ntia_range_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            ItmConfiguration(
                climate=ItmClimate.CONTINENTAL_TEMPERATE,
                polarization=ItmPolarization.VERTICAL,
                variability_mode=ItmVariabilityMode.BROADCAST,
                surface_refractivity_n_units=401.0,
                ground_dielectric_constant=15.0,
                ground_conductivity_s_per_m=0.005,
                confidence=0.50,
                reliability=0.50,
            )

    def test_dielectric_constant_must_exceed_one(self):
        with self.assertRaises(
            ValueError
        ):
            ItmConfiguration(
                climate=ItmClimate.CONTINENTAL_TEMPERATE,
                polarization=ItmPolarization.VERTICAL,
                variability_mode=ItmVariabilityMode.BROADCAST,
                surface_refractivity_n_units=301.0,
                ground_dielectric_constant=1.0,
                ground_conductivity_s_per_m=0.005,
                confidence=0.50,
                reliability=0.50,
            )

    def test_invalid_conductivity_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            ItmConfiguration(
                climate=ItmClimate.CONTINENTAL_TEMPERATE,
                polarization=ItmPolarization.VERTICAL,
                variability_mode=ItmVariabilityMode.BROADCAST,
                surface_refractivity_n_units=301.0,
                ground_dielectric_constant=15.0,
                ground_conductivity_s_per_m=0.0,
                confidence=0.50,
                reliability=0.50,
            )

    def test_confidence_zero_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            ItmConfiguration(
                climate=ItmClimate.CONTINENTAL_TEMPERATE,
                polarization=ItmPolarization.VERTICAL,
                variability_mode=ItmVariabilityMode.BROADCAST,
                surface_refractivity_n_units=301.0,
                ground_dielectric_constant=15.0,
                ground_conductivity_s_per_m=0.005,
                confidence=0.0,
                reliability=0.50,
            )

    def test_reliability_one_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            ItmConfiguration(
                climate=ItmClimate.CONTINENTAL_TEMPERATE,
                polarization=ItmPolarization.VERTICAL,
                variability_mode=ItmVariabilityMode.BROADCAST,
                surface_refractivity_n_units=301.0,
                ground_dielectric_constant=15.0,
                ground_conductivity_s_per_m=0.005,
                confidence=0.50,
                reliability=1.0,
            )

    def test_terrain_profile_conversion(self):
        terrain = terrain_profile_to_itm(
            self._make_profile()
        )

        self.assertIsInstance(
            terrain,
            ItmTerrainProfile,
        )

        self.assertEqual(
            terrain.sample_count,
            3,
        )

        self.assertEqual(
            terrain.interval_count,
            2,
        )

        self.assertEqual(
            terrain.sample_spacing_m,
            30.0,
        )

    def test_pfl_format(self):
        terrain = terrain_profile_to_itm(
            self._make_profile()
        )

        pfl = terrain.to_pfl()

        self.assertEqual(
            pfl,
            (
                2.0,
                30.0,
                30.0,
                35.0,
                33.0,
            ),
        )

    def test_itm_terrain_total_distance(self):
        terrain = ItmTerrainProfile(
            sample_spacing_m=30.0,
            elevations_m=(
                10.0,
                20.0,
                30.0,
                40.0,
            ),
        )

        self.assertEqual(
            terrain.total_distance_m,
            90.0,
        )

    def test_irregular_spacing_rejected(self):
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
                distance_m=30.0,
                latitude=28.0,
                longitude=-80.9997,
                x_m=500030.0,
                y_m=3200000.0,
                elevation_m=35.0,
            ),
            TerrainProfileSample(
                distance_m=70.0,
                latitude=28.0,
                longitude=-80.9993,
                x_m=500070.0,
                y_m=3200000.0,
                elevation_m=33.0,
            ),
        )

        profile = TerrainProfile(
            raster_path="terrain.tif",
            raster_crs="EPSG:32617",
            total_distance_m=70.0,
            requested_spacing_m=30.0,
            actual_spacing_m=35.0,
            samples=samples,
        )

        with self.assertRaises(
            ValueError
        ):
            terrain_profile_to_itm(
                profile
            )

    def test_tx_height_below_ntia_limit_rejected(self):
        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=0.4,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        with self.assertRaises(
            ValueError
        ):
            prepare_itm_request(
                request,
                self._make_configuration(),
            )

    def test_rx_height_above_ntia_limit_rejected(self):
        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=3001.0,
            terrain_profile=self._make_profile(),
        )

        with self.assertRaises(
            ValueError
        ):
            prepare_itm_request(
                request,
                self._make_configuration(),
            )

    def test_prepare_itm_request(self):
        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        prepared = prepare_itm_request(
            request=request,
            configuration=(
                self._make_configuration()
            ),
        )

        self.assertIsInstance(
            prepared,
            ItmPreparedRequest,
        )

        self.assertIsInstance(
            prepared.native_input,
            ItmNativeInput,
        )

        self.assertEqual(
            prepared.native_input.frequency_mhz,
            600.0,
        )

        self.assertEqual(
            prepared.native_input.variability_mode,
            3,
        )

    def test_probability_fractions_convert_to_percent(self):
        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        prepared = prepare_itm_request(
            request=request,
            configuration=(
                self._make_configuration()
            ),
        )

        self.assertEqual(
            prepared.native_input.confidence_percent,
            50.0,
        )

        self.assertEqual(
            prepared.native_input.reliability_percent,
            50.0,
        )

    def test_native_pfl_is_preserved(self):
        request = PropagationRequest(
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_profile=self._make_profile(),
        )

        prepared = prepare_itm_request(
            request=request,
            configuration=(
                self._make_configuration()
            ),
        )

        self.assertEqual(
            prepared.native_input.pfl[0],
            2.0,
        )

        self.assertEqual(
            prepared.native_input.pfl[1],
            30.0,
        )

        self.assertEqual(
            len(
                prepared.native_input.pfl
            ),
            5,
        )


if __name__ == "__main__":
    unittest.main()