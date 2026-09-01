import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from geovaris_rf.rapid_worker import (
    RAPID_CLUTTER_SOURCE,
    RAPID_CLUTTER_VERSION,
    RAPID_DEM_HORIZONTAL_CRS,
    RAPID_DEM_RESOLUTION_M,
    RAPID_DEM_SOURCE,
    RAPID_DEM_UNITS,
    RAPID_DEM_VERSION,
    RAPID_DEM_VERTICAL_DATUM,
    RAPID_RESOLUTION_M,
    _resolve_required_file,
    _validate_run,
    fail_rapid_run,
    get_requested_run_id,
)
from geovaris_rf.clutter_height import (
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME,
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION,
)
from geovaris_rf.rapid_run_completion import (
    RAPID_PROPAGATION_MODEL,
    RAPID_PROPAGATION_MODEL_VERSION,
)


class RapidWorkerTests(
    unittest.TestCase
):
    def _valid_run(
        self,
    ) -> dict:
        return {
            "id": "run-123",
            "customer_id": "customer-123",
            "scenario_id": "scenario-123",

            "site_latitude": 28.6,
            "site_longitude": -81.3,
            "site_ground_elevation_m": 20.0,

            "frequency_mhz": 600.0,
            "eirp_watts": 1000.0,

            "antenna_height_m": 54.864,
            "antenna_gain_dbi": 0.0,

            "receiver_height_m": 1.5,
            "receiver_threshold_dbm": -95.0,

            "calculation_radius_m": 48280.32,
            "resolution_m": RAPID_RESOLUTION_M,

            "propagation_model": (
                RAPID_PROPAGATION_MODEL
            ),
            "propagation_model_version": (
                RAPID_PROPAGATION_MODEL_VERSION
            ),

            "itm_climate": None,
            "itm_polarization": None,
            "itm_variability_mode": None,
            "itm_surface_refractivity": None,
            "itm_dielectric_constant": None,
            "itm_conductivity_s_per_m": None,
            "itm_confidence": None,
            "itm_reliability": None,

            "clutter_source": (
                RAPID_CLUTTER_SOURCE
            ),
            "clutter_version": (
                RAPID_CLUTTER_VERSION
            ),
            "clutter_model": (
                GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME
            ),
            "clutter_model_version": (
                GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION
            ),
            "clutter_percentage_locations": None,
            "clutter_correction_end": None,

            "dem_source": RAPID_DEM_SOURCE,
            "dem_version": RAPID_DEM_VERSION,
            "dem_horizontal_crs": RAPID_DEM_HORIZONTAL_CRS,
            "dem_vertical_datum": RAPID_DEM_VERTICAL_DATUM,
            "dem_units": RAPID_DEM_UNITS,
            "dem_resolution_m": RAPID_DEM_RESOLUTION_M,
        }

    def test_valid_run_is_accepted(
        self,
    ) -> None:
        _validate_run(
            self._valid_run()
        )

    def test_wrong_model_rejected(
        self,
    ) -> None:
        run = self._valid_run()

        run[
            "propagation_model"
        ] = "ntia_itm"

        with self.assertRaisesRegex(
            ValueError,
            "not a rapid_coverage run",
        ):
            _validate_run(
                run
            )

    def test_wrong_model_version_rejected(
        self,
    ) -> None:
        run = self._valid_run()

        run[
            "propagation_model_version"
        ] = "old-version"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported Rapid Coverage model version",
        ):
            _validate_run(
                run
            )

    def test_wrong_resolution_rejected(
        self,
    ) -> None:
        run = self._valid_run()

        run[
            "resolution_m"
        ] = 250.0

        with self.assertRaisesRegex(
            ValueError,
            "30 m resolution",
        ):
            _validate_run(
                run
            )

    def test_wrong_clutter_profile_rejected(
        self,
    ) -> None:
        run = self._valid_run()

        run[
            "clutter_model"
        ] = "Some Other Profile"

        with self.assertRaisesRegex(
            ValueError,
            "Unsupported Rapid Coverage clutter model",
        ):
            _validate_run(
                run
            )

    def test_itm_assumptions_rejected(
        self,
    ) -> None:
        run = self._valid_run()

        run[
            "itm_climate"
        ] = 5

        with self.assertRaisesRegex(
            ValueError,
            "must not contain ITM assumptions",
        ):
            _validate_run(
                run
            )

    def test_p2108_percentage_rejected(
        self,
    ) -> None:
        run = self._valid_run()

        run[
            "clutter_percentage_locations"
        ] = 50.0

        with self.assertRaisesRegex(
            ValueError,
            "P.2108 clutter percentage",
        ):
            _validate_run(
                run
            )

    def test_requested_run_id_is_trimmed(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "GEOVARIS_COVERAGE_RUN_ID":
                    "  run-123  ",
            },
        ):
            self.assertEqual(
                get_requested_run_id(),
                "run-123",
            )

    def test_blank_requested_run_id_becomes_none(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "GEOVARIS_COVERAGE_RUN_ID":
                    "   ",
            },
        ):
            self.assertIsNone(
                get_requested_run_id()
            )

    def test_required_file_is_resolved(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = (
                Path(
                    temp_dir
                )
                / "input.tif"
            )

            path.write_bytes(
                b"test"
            )

            with patch.dict(
                os.environ,
                {
                    "GEOVARIS_TEST_FILE":
                        str(
                            path
                        ),
                },
            ):
                result = (
                    _resolve_required_file(
                        environment_variable=(
                            "GEOVARIS_TEST_FILE"
                        ),
                        description=(
                            "test file"
                        ),
                    )
                )

            self.assertEqual(
                result,
                path.resolve(),
            )

    def test_missing_required_file_rejected(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "must be configured",
            ):
                _resolve_required_file(
                    environment_variable=(
                        "GEOVARIS_TEST_FILE"
                    ),
                    description=(
                        "test file"
                    ),
                )

    def test_fail_run_updates_database(
        self,
    ) -> None:
        connection = MagicMock()
        cursor = MagicMock()

        connection.cursor.return_value.__enter__.return_value = (
            cursor
        )

        fail_rapid_run(
            connection,
            run_id="run-123",
            error_message="test failure",
        )

        cursor.execute.assert_called_once()

        sql_text = (
            cursor.execute.call_args[
                0
            ][
                0
            ]
        )

        params = (
            cursor.execute.call_args[
                0
            ][
                1
            ]
        )

        self.assertIn(
            "status = 'failed'",
            sql_text,
        )

        self.assertEqual(
            params[
                0
            ],
            "test failure",
        )

        self.assertEqual(
            params[
                1
            ],
            "run-123",
        )

        connection.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
    