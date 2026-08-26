import tempfile
import unittest
from pathlib import Path

import rasterio

from geovaris_rf.coverage_calculation import (
    CoverageCalculationResult,
    CoverageCellResult,
    CoverageCellStatus,
)
from geovaris_rf.coverage_grid import (
    plan_coverage_grid,
)
from geovaris_rf.coverage_raster import (
    DEFAULT_FLOAT_NODATA,
    CoverageRasterResult,
    write_coverage_geotiff,
)


class CoverageRasterTests(
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

    def _make_calculation(
        self,
        grid,
    ) -> CoverageCalculationResult:
        center_row = (
            grid.height // 2
        )

        center_column = (
            grid.width // 2
        )

        evaluated_point = next(
            point
            for point in grid.points
            if (
                point.inside_radius
                and not (
                    point.row == center_row
                    and point.column == center_column
                )
            )
        )

        center_point = next(
            point
            for point in grid.points
            if (
                point.row == center_row
                and point.column == center_column
            )
        )

        cells = (
            CoverageCellResult(
                row=center_point.row,
                column=center_point.column,
                latitude=center_point.latitude,
                longitude=center_point.longitude,
                distance_from_site_m=0.0,
                status=(
                    CoverageCellStatus.TRANSMITTER_SITE
                ),
            ),
            CoverageCellResult(
                row=evaluated_point.row,
                column=evaluated_point.column,
                latitude=evaluated_point.latitude,
                longitude=evaluated_point.longitude,
                distance_from_site_m=(
                    evaluated_point.distance_from_site_m
                ),
                status=CoverageCellStatus.EVALUATED,
                propagation_loss_db=120.0,
                predicted_received_power_dbm=-60.0,
                receiver_threshold_dbm=-90.0,
                margin_db=30.0,
                meets_threshold=True,
                propagation_mode="line_of_sight",
                warnings=(),
            ),
        )

        return CoverageCalculationResult(
            model_name="NTIA ITM",
            model_version="1.4",
            requested_cell_limit=1,
            evaluated_cell_count=1,
            transmitter_site_cell_count=1,
            covered_cell_count=1,
            uncovered_cell_count=0,
            cells=cells,
        )

    def test_writes_geotiff(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            result = write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            self.assertIsInstance(
                result,
                CoverageRasterResult,
            )

            self.assertTrue(
                output_path.exists()
            )

    def test_raster_dimensions_match_grid(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                self.assertEqual(
                    dataset.width,
                    grid.width,
                )

                self.assertEqual(
                    dataset.height,
                    grid.height,
                )

                self.assertEqual(
                    dataset.count,
                    3,
                )

    def test_raster_crs_matches_grid(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                self.assertEqual(
                    dataset.crs.to_epsg(),
                    grid.crs_epsg,
                )

    def test_evaluated_cell_values_are_written(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        evaluated = next(
            cell
            for cell in calculation.cells
            if (
                cell.status
                == CoverageCellStatus.EVALUATED
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                received = dataset.read(
                    1
                )

                margin = dataset.read(
                    2
                )

                mask = dataset.read(
                    3
                )

                self.assertEqual(
                    received[
                        evaluated.row,
                        evaluated.column,
                    ],
                    -60.0,
                )

                self.assertEqual(
                    margin[
                        evaluated.row,
                        evaluated.column,
                    ],
                    30.0,
                )

                self.assertEqual(
                    mask[
                        evaluated.row,
                        evaluated.column,
                    ],
                    1.0,
                )

    def test_transmitter_cell_is_nodata(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        tx_cell = next(
            cell
            for cell in calculation.cells
            if (
                cell.status
                == CoverageCellStatus.TRANSMITTER_SITE
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                received = dataset.read(
                    1
                )

                self.assertEqual(
                    received[
                        tx_cell.row,
                        tx_cell.column,
                    ],
                    DEFAULT_FLOAT_NODATA,
                )

    def test_band_descriptions_written(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                self.assertEqual(
                    dataset.descriptions[0],
                    "Predicted received power (dBm)",
                )

                self.assertEqual(
                    dataset.descriptions[1],
                    "Receiver threshold margin (dB)",
                )

    def test_model_lineage_tags_written(
        self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                tags = dataset.tags()

                self.assertEqual(
                    tags[
                        "model_name"
                    ],
                    "NTIA ITM",
                )

                self.assertEqual(
                    tags[
                        "model_version"
                    ],
                    "1.4",
                )
    def test_unevaluated_mask_cells_are_nodata(
    self,
    ):
        grid = self._make_grid()

        calculation = (
            self._make_calculation(
                grid
            )
        )

        evaluated_locations = {
            (
                cell.row,
                cell.column,
            )
            for cell in calculation.cells
        }

        unevaluated_point = next(
            point
            for point in grid.points
            if (
                point.row,
                point.column,
            )
            not in evaluated_locations
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "coverage.tif"
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    output_path
                ),
            )

            with rasterio.open(
                output_path
            ) as dataset:
                mask = dataset.read(
                    3
                )

                self.assertEqual(
                    mask[
                        unevaluated_point.row,
                        unevaluated_point.column,
                    ],
                    DEFAULT_FLOAT_NODATA,
                )


if __name__ == "__main__":
    unittest.main()