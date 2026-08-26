import unittest
from unittest.mock import patch

from geovaris_rf.coverage_calculation import (
    CoverageCellStatus,
    calculate_coverage_subset,
)
from geovaris_rf.coverage_grid import (
    plan_coverage_grid,
)
from geovaris_rf.path_evaluation import (
    PathEvaluationResult,
)
from geovaris_rf.link_budget import (
    LinkBudgetResult,
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
            assumptions={},
        )


class CoverageCalculationTests(
    unittest.TestCase
):
    def _make_grid(
        self,
    ):
        return plan_coverage_grid(
            28.5383,
            -81.3792,
            1000.0,
            500.0,
        )

    def _make_profile(
        self,
    ) -> TerrainProfile:
        samples = (
            TerrainProfileSample(
                distance_m=0.0,
                latitude=28.5383,
                longitude=-81.3792,
                x_m=500000.0,
                y_m=3200000.0,
                elevation_m=30.0,
            ),
            TerrainProfileSample(
                distance_m=500.0,
                latitude=28.54,
                longitude=-81.3792,
                x_m=500000.0,
                y_m=3200500.0,
                elevation_m=32.0,
            ),
        )

        return TerrainProfile(
            raster_path="terrain.tif",
            raster_crs="EPSG:32617",
            total_distance_m=500.0,
            requested_spacing_m=500.0,
            actual_spacing_m=500.0,
            samples=samples,
        )

    @patch(
        "geovaris_rf.coverage_calculation.sample_terrain_profile"
    )
    def test_subset_respects_cell_limit(
        self,
        mock_sample,
    ):
        mock_sample.return_value = (
            self._make_profile()
        )

        result = calculate_coverage_subset(
            model=DummyPropagationModel(),
            grid=self._make_grid(),
            dem_raster_path="terrain.tif",
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_sample_spacing_m=30.0,
            eirp_dbm=60.0,
            receiver_gain_dbi=0.0,
            additional_losses_db=0.0,
            receiver_threshold_dbm=-90.0,
            max_propagation_cells=3,
        )

        self.assertEqual(
            result.evaluated_cell_count,
            3,
        )

    @patch(
        "geovaris_rf.coverage_calculation.sample_terrain_profile"
    )
    def test_link_budget_is_preserved(
        self,
        mock_sample,
    ):
        mock_sample.return_value = (
            self._make_profile()
        )

        result = calculate_coverage_subset(
            model=DummyPropagationModel(),
            grid=self._make_grid(),
            dem_raster_path="terrain.tif",
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_sample_spacing_m=30.0,
            eirp_dbm=60.0,
            receiver_gain_dbi=0.0,
            additional_losses_db=0.0,
            receiver_threshold_dbm=-90.0,
            max_propagation_cells=1,
        )

        evaluated = next(
            cell
            for cell in result.cells
            if (
                cell.status
                == CoverageCellStatus.EVALUATED
            )
        )

        self.assertEqual(
            evaluated.propagation_loss_db,
            120.0,
        )

        self.assertEqual(
            evaluated.predicted_received_power_dbm,
            -60.0,
        )

        self.assertEqual(
            evaluated.margin_db,
            30.0,
        )

        self.assertTrue(
            evaluated.meets_threshold
        )

    @patch(
        "geovaris_rf.coverage_calculation.sample_terrain_profile"
    )
    def test_summary_counts_covered_cells(
        self,
        mock_sample,
    ):
        mock_sample.return_value = (
            self._make_profile()
        )

        result = calculate_coverage_subset(
            model=DummyPropagationModel(),
            grid=self._make_grid(),
            dem_raster_path="terrain.tif",
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_sample_spacing_m=30.0,
            eirp_dbm=60.0,
            receiver_gain_dbi=0.0,
            additional_losses_db=0.0,
            receiver_threshold_dbm=-90.0,
            max_propagation_cells=2,
        )

        self.assertEqual(
            result.covered_cell_count,
            2,
        )

        self.assertEqual(
            result.uncovered_cell_count,
            0,
        )

    @patch(
        "geovaris_rf.coverage_calculation.sample_terrain_profile"
    )
    def test_model_lineage_is_preserved(
        self,
        mock_sample,
    ):
        mock_sample.return_value = (
            self._make_profile()
        )

        result = calculate_coverage_subset(
            model=DummyPropagationModel(),
            grid=self._make_grid(),
            dem_raster_path="terrain.tif",
            frequency_mhz=600.0,
            transmitter_height_agl_m=45.72,
            receiver_height_agl_m=2.0,
            terrain_sample_spacing_m=30.0,
            eirp_dbm=60.0,
            receiver_gain_dbi=0.0,
            additional_losses_db=0.0,
            receiver_threshold_dbm=-90.0,
            max_propagation_cells=1,
        )

        self.assertEqual(
            result.model_name,
            "Dummy Model",
        )

        self.assertEqual(
            result.model_version,
            "1.0",
        )

    def test_zero_cell_limit_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            calculate_coverage_subset(
                model=DummyPropagationModel(),
                grid=self._make_grid(),
                dem_raster_path="terrain.tif",
                frequency_mhz=600.0,
                transmitter_height_agl_m=45.72,
                receiver_height_agl_m=2.0,
                terrain_sample_spacing_m=30.0,
                eirp_dbm=60.0,
                receiver_gain_dbi=0.0,
                additional_losses_db=0.0,
                receiver_threshold_dbm=-90.0,
                max_propagation_cells=0,
            )


if __name__ == "__main__":
    unittest.main()