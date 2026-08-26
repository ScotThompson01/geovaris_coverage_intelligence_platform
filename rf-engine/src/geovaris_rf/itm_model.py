"""GeoVaris propagation-model adapter for NTIA ITM.

This module connects the GeoVaris PropagationModel interface to the
low-level NTIA ITM native DLL adapter.

ITM output is an engineering propagation estimate. It is not a
guarantee of service availability.
"""

from __future__ import annotations

from pathlib import Path

from geovaris_rf.itm import (
    ItmConfiguration,
    prepare_itm_request,
)
from geovaris_rf.itm_native import (
    ItmNativeLibrary,
)
from geovaris_rf.propagation import (
    PropagationModel,
    PropagationRequest,
    PropagationResult,
)


PROPAGATION_MODE_NAMES = {
    1: "line_of_sight",
    2: "diffraction",
    3: "troposcatter",
}


class ItmModel(
    PropagationModel
):
    """GeoVaris NTIA ITM propagation model."""

    def __init__(
        self,
        dll_path: str,
        configuration: ItmConfiguration,
        model_version: str = "1.4",
    ) -> None:
        self._configuration = (
            configuration
        )

        self._model_version = (
            model_version
        )

        self._native_library = (
            ItmNativeLibrary(
                dll_path
            )
        )

    @property
    def model_name(self) -> str:
        return "NTIA ITM"

    @property
    def model_version(self) -> str:
        return self._model_version

    def calculate(
        self,
        request: PropagationRequest,
    ) -> PropagationResult:
        """Calculate point-to-point ITM transmission loss."""

        prepared = prepare_itm_request(
            request=request,
            configuration=(
                self._configuration
            ),
        )

        native_result = (
            self._native_library
            .calculate_p2p_cr(
                prepared.native_input
            )
        )

        if native_result.return_code != 0:
            raise RuntimeError(
                "NTIA ITM calculation failed with "
                f"return code "
                f"{native_result.return_code}."
            )

        propagation_mode = (
            PROPAGATION_MODE_NAMES.get(
                native_result
                .intermediate
                .propagation_mode,
                (
                    "unknown_"
                    f"{native_result.intermediate.propagation_mode}"
                ),
            )
        )

        warnings: tuple[str, ...] = ()

        if native_result.warning_flags != 0:
            warnings = (
                (
                    "NTIA ITM warning flags: "
                    f"0x{native_result.warning_flags:04X}"
                ),
            )

        assumptions = {
            "climate": int(
                self._configuration.climate
            ),
            "polarization": int(
                self._configuration.polarization
            ),
            "variability_mode": int(
                self._configuration.variability_mode
            ),
            "surface_refractivity_n_units": (
                self._configuration
                .surface_refractivity_n_units
            ),
            "ground_dielectric_constant": (
                self._configuration
                .ground_dielectric_constant
            ),
            "ground_conductivity_s_per_m": (
                self._configuration
                .ground_conductivity_s_per_m
            ),
            "confidence": (
                self._configuration.confidence
            ),
            "reliability": (
                self._configuration.reliability
            ),
            "itm_return_code": (
                native_result.return_code
            ),
            "itm_warning_flags": (
                native_result.warning_flags
            ),
            "free_space_loss_db": (
                native_result
                .intermediate
                .free_space_loss_db
            ),
            "reference_attenuation_db": (
                native_result
                .intermediate
                .reference_attenuation_db
            ),
            "terrain_irregularity_m": (
                native_result
                .intermediate
                .terrain_irregularity_m
            ),
            "path_distance_km": (
                native_result
                .intermediate
                .path_distance_km
            ),
            "native_propagation_mode": (
                native_result
                .intermediate
                .propagation_mode
            ),
        }

        return PropagationResult(
            model_name=self.model_name,
            model_version=self.model_version,
            basic_transmission_loss_db=(
                native_result
                .basic_transmission_loss_db
            ),
            propagation_mode=(
                propagation_mode
            ),
            warnings=warnings,
            assumptions=assumptions,
        )


def default_local_itm_dll_path() -> str:
    """Return the expected local development DLL path.

    This helper is only for local development/testing.
    Production deployment should provision the native library
    explicitly rather than depend on repository-relative paths.
    """

    rf_engine_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    return str(
        rf_engine_root
        / "vendor"
        / "ntia-itm"
        / "itm.dll"
    )