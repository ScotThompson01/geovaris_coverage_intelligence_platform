import math
import unittest

from geovaris_rf.terrain_analysis import (
    DEFAULT_K_FACTOR,
    MEAN_EARTH_RADIUS_M,
    TerrainPathAnalysis,
    TerrainPathAnalysisSample,
    analyze_terrain_path,
    calculate_earth_curvature_bulge_m,
    calculate_first_fresnel_radius_m,
    calculate_wavelength_m,
)
from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
)


class TerrainAnalysisTests(unittest.TestCase):
    def _make_profile(
        self,
        elevations: list[float],
        spacing_m: float = 100.0,
    ) -> TerrainProfile:
        samples = []

        for index, elevation_m in enumerate(
            elevations
        ):
            samples.append(
                TerrainProfileSample(
                    distance_m=index * spacing_m,
                    latitude=28.0,
                    longitude=-81.0,
                    x_m=500000.0 + index * spacing_m,
                    y_m=3200000.0,
                    elevation_m=elevation_m,
                )
            )

        total_distance_m = (
            (len(elevations) - 1)
            * spacing_m
        )

        return TerrainProfile(
            raster_path="terrain.tif",
            raster_crs="EPSG:32617",
            total_distance_m=total_distance_m,
            requested_spacing_m=spacing_m,
            actual_spacing_m=(
                spacing_m
                if len(elevations) > 1
                else 0.0
            ),
            samples=tuple(samples),
        )

    def test_wavelength_at_600_mhz(self):
        wavelength_m = calculate_wavelength_m(
            600.0
        )

        self.assertAlmostEqual(
            wavelength_m,
            0.4996540967,
            places=6,
        )

    def test_wavelength_at_6000_mhz(self):
        wavelength_m = calculate_wavelength_m(
            6000.0
        )

        self.assertAlmostEqual(
            wavelength_m,
            0.0499654097,
            places=6,
        )

    def test_frequency_below_supported_range_rejected(self):
        with self.assertRaises(ValueError):
            calculate_wavelength_m(
                599.0
            )

    def test_frequency_above_supported_range_rejected(self):
        with self.assertRaises(ValueError):
            calculate_wavelength_m(
                6001.0
            )

    def test_fresnel_radius_is_zero_at_endpoint(self):
        radius_m = calculate_first_fresnel_radius_m(
            frequency_mhz=600.0,
            distance_from_tx_m=0.0,
            distance_to_rx_m=10_000.0,
        )

        self.assertEqual(
            radius_m,
            0.0,
        )

    def test_fresnel_radius_at_path_midpoint(self):
        radius_m = calculate_first_fresnel_radius_m(
            frequency_mhz=600.0,
            distance_from_tx_m=5000.0,
            distance_to_rx_m=5000.0,
        )

        wavelength_m = calculate_wavelength_m(
            600.0
        )

        expected_m = math.sqrt(
            wavelength_m
            * 5000.0
            * 5000.0
            / 10_000.0
        )

        self.assertAlmostEqual(
            radius_m,
            expected_m,
            places=9,
        )

    def test_curvature_is_zero_at_endpoint(self):
        bulge_m = calculate_earth_curvature_bulge_m(
            distance_from_tx_m=0.0,
            distance_to_rx_m=10_000.0,
        )

        self.assertEqual(
            bulge_m,
            0.0,
        )

    def test_curvature_midpoint_matches_formula(self):
        bulge_m = calculate_earth_curvature_bulge_m(
            distance_from_tx_m=5000.0,
            distance_to_rx_m=5000.0,
            k_factor=4.0 / 3.0,
        )

        expected_m = (
            5000.0
            * 5000.0
            / (
                2.0
                * MEAN_EARTH_RADIUS_M
                * (4.0 / 3.0)
            )
        )

        self.assertAlmostEqual(
            bulge_m,
            expected_m,
            places=9,
        )

    def test_larger_k_factor_reduces_curvature(self):
        standard_bulge = (
            calculate_earth_curvature_bulge_m(
                distance_from_tx_m=5000.0,
                distance_to_rx_m=5000.0,
                k_factor=1.0,
            )
        )

        refracted_bulge = (
            calculate_earth_curvature_bulge_m(
                distance_from_tx_m=5000.0,
                distance_to_rx_m=5000.0,
                k_factor=4.0 / 3.0,
            )
        )

        self.assertLess(
            refracted_bulge,
            standard_bulge,
        )

    def test_invalid_k_factor_rejected(self):
        with self.assertRaises(ValueError):
            calculate_earth_curvature_bulge_m(
                distance_from_tx_m=5000.0,
                distance_to_rx_m=5000.0,
                k_factor=0.0,
            )

    def test_analysis_sample_preserves_metadata(self):
        sample = TerrainPathAnalysisSample(
            sample_index=1,
            distance_m=100.0,
            terrain_elevation_m=30.0,
            los_elevation_m=50.0,
            earth_curvature_bulge_m=1.0,
            effective_terrain_elevation_m=31.0,
            geometric_terrain_clearance_m=20.0,
            curvature_adjusted_terrain_clearance_m=19.0,
            first_fresnel_radius_m=5.0,
            geometric_first_fresnel_clearance_m=15.0,
            curvature_adjusted_first_fresnel_clearance_m=14.0,
            sixty_percent_fresnel_radius_m=3.0,
            geometric_sixty_percent_fresnel_clearance_m=17.0,
            curvature_adjusted_sixty_percent_fresnel_clearance_m=16.0,
        )

        self.assertEqual(
            sample.sample_index,
            1,
        )

        self.assertEqual(
            sample.earth_curvature_bulge_m,
            1.0,
        )

    def test_flat_path_has_geometric_los(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                30.0,
                30.0,
                30.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=10.0,
        )

        self.assertTrue(
            analysis.geometric_los_clear
        )

    def test_high_terrain_obstruction_blocks_geometric_los(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                100.0,
                30.0,
                30.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=20.0,
            receiver_height_agl_m=10.0,
        )

        self.assertFalse(
            analysis.geometric_los_clear
        )

        self.assertEqual(
            analysis.worst_geometric_terrain_sample_index,
            2,
        )

    def test_endpoint_is_excluded_from_obstruction_ranking(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                30.0,
                30.0,
                30.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=2.0,
        )

        self.assertNotEqual(
            analysis.worst_geometric_terrain_sample_index,
            0,
        )

        self.assertNotEqual(
            analysis.worst_geometric_terrain_sample_index,
            4,
        )

    def test_curvature_reduces_clearance(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                30.0,
            ],
            spacing_m=5000.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=30.0,
            k_factor=4.0 / 3.0,
        )

        midpoint = analysis.samples[1]

        self.assertLess(
            midpoint.curvature_adjusted_terrain_clearance_m,
            midpoint.geometric_terrain_clearance_m,
        )

    def test_analysis_records_k_factor(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                30.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=900.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=10.0,
            k_factor=1.25,
        )

        self.assertEqual(
            analysis.k_factor,
            1.25,
        )

        self.assertAlmostEqual(
            analysis.effective_earth_radius_m,
            MEAN_EARTH_RADIUS_M * 1.25,
        )

    def test_default_k_factor_is_four_thirds(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                30.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=10.0,
        )

        self.assertEqual(
            analysis.k_factor,
            DEFAULT_K_FACTOR,
        )

    def test_fresnel_can_fail_even_with_geometric_los(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
                30.0,
                30.0,
                30.0,
            ],
            spacing_m=2500.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=20.0,
            receiver_height_agl_m=20.0,
        )

        self.assertTrue(
            analysis.geometric_los_clear
        )

        self.assertFalse(
            analysis.geometric_first_fresnel_clear
        )

    def test_sixty_percent_fresnel_radius_is_60_percent(self):
        profile = self._make_profile(
            [
                0.0,
                0.0,
                0.0,
            ],
            spacing_m=5000.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=100.0,
            receiver_height_agl_m=100.0,
        )

        midpoint = analysis.samples[1]

        self.assertAlmostEqual(
            midpoint.sixty_percent_fresnel_radius_m,
            midpoint.first_fresnel_radius_m * 0.60,
            places=9,
        )

    def test_antenna_amsl_uses_ground_plus_agl(self):
        profile = self._make_profile(
            [
                35.0,
                40.0,
                45.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=900.0,
            transmitter_height_agl_m=50.0,
            receiver_height_agl_m=2.0,
        )

        self.assertEqual(
            analysis.transmitter_antenna_elevation_m,
            85.0,
        )

        self.assertEqual(
            analysis.receiver_antenna_elevation_m,
            47.0,
        )

    def test_negative_transmitter_height_rejected(self):
        profile = self._make_profile(
            [
                30.0,
                30.0,
            ]
        )

        with self.assertRaises(ValueError):
            analyze_terrain_path(
                profile=profile,
                frequency_mhz=600.0,
                transmitter_height_agl_m=-1.0,
                receiver_height_agl_m=2.0,
            )

    def test_analysis_preserves_summary_metadata(self):
        profile = self._make_profile(
            [
                10.0,
                10.0,
                10.0,
            ],
            spacing_m=100.0,
        )

        analysis = analyze_terrain_path(
            profile=profile,
            frequency_mhz=600.0,
            transmitter_height_agl_m=30.0,
            receiver_height_agl_m=10.0,
        )

        self.assertIsInstance(
            analysis,
            TerrainPathAnalysis,
        )

        self.assertEqual(
            analysis.frequency_mhz,
            600.0,
        )

        self.assertEqual(
            len(analysis.samples),
            3,
        )


if __name__ == "__main__":
    unittest.main()