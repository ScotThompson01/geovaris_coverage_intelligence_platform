import unittest
from pathlib import Path

from geovaris_rf.itm import (
    ItmNativeInput,
)
from geovaris_rf.itm_native import (
    ItmNativeLibrary,
    ItmNativeResult,
)


class ItmNativeTests(
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

        cls.reference_pfl_path = (
            rf_engine_root
            / "vendor"
            / "ntia-itm"
            / "itm-1.4"
            / "cmd_examples"
            / "pfl.txt"
        )

    def _load_reference_pfl(
        self,
    ) -> tuple[float, ...]:
        if not self.reference_pfl_path.exists():
            self.skipTest(
                "Official NTIA reference PFL "
                "is not installed locally."
            )

        raw_text = (
            self.reference_pfl_path
            .read_text(
                encoding="utf-8"
            )
            .strip()
        )

        return tuple(
            float(value.strip())
            for value in raw_text.split(",")
            if value.strip()
        )

    def test_missing_dll_rejected(self):
        with self.assertRaises(
            FileNotFoundError
        ):
            ItmNativeLibrary(
                "this-file-does-not-exist.dll"
            )

    def test_official_ntia_reference_case(
        self,
    ):
        if not self.dll_path.exists():
            self.skipTest(
                "Official NTIA itm.dll "
                "is not installed locally."
            )

        pfl = (
            self._load_reference_pfl()
        )

        native_input = ItmNativeInput(
            pfl=pfl,

            transmitter_height_m=15.0,
            receiver_height_m=3.0,

            climate=5,

            surface_refractivity_n_units=301.0,

            frequency_mhz=3500.0,

            polarization=1,

            ground_dielectric_constant=15.0,

            ground_conductivity_s_per_m=0.005,

            variability_mode=1,

            confidence_percent=50.0,
            reliability_percent=50.0,
        )

        library = ItmNativeLibrary(
            str(
                self.dll_path
            )
        )

        result = (
            library.calculate_p2p_cr(
                native_input
            )
        )

        self.assertIsInstance(
            result,
            ItmNativeResult,
        )

        self.assertEqual(
            result.return_code,
            0,
        )

        self.assertEqual(
            result.warning_flags,
            0,
        )

        self.assertAlmostEqual(
            result.basic_transmission_loss_db,
            114.5,
            places=1,
        )

        self.assertAlmostEqual(
            result.intermediate.free_space_loss_db,
            114.5,
            places=1,
        )

        self.assertAlmostEqual(
            result.intermediate.path_distance_km,
            3.635,
            places=3,
        )

        self.assertAlmostEqual(
            result.intermediate.terrain_irregularity_m,
            3.2,
            places=1,
        )

        self.assertEqual(
            result.intermediate.propagation_mode,
            1,
        )


if __name__ == "__main__":
    unittest.main()