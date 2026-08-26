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


ITM_WARNING_FLAGS = {
    0x0001: "WARN__TX_TERMINAL_HEIGHT",
    0x0002: "WARN__RX_TERMINAL_HEIGHT",
    0x0004: "WARN__FREQUENCY",
    0x0008: "WARN__PATH_DISTANCE_TOO_BIG_1",
    0x0010: "WARN__PATH_DISTANCE_TOO_BIG_2",
    0x0020: "WARN__PATH_DISTANCE_TOO_SMALL_1",
    0x0040: "WARN__PATH_DISTANCE_TOO_SMALL_2",
    0x0080: "WARN__TX_HORIZON_ANGLE",
    0x0100: "WARN__RX_HORIZON_ANGLE",
    0x0200: "WARN__TX_HORIZON_DISTANCE_1",
    0x0400: "WARN__RX_HORIZON_DISTANCE_1",
    0x0800: "WARN__TX_HORIZON_DISTANCE_2",
    0x1000: "WARN__RX_HORIZON_DISTANCE_2",
    0x2000: "WARN__EXTREME_VARIABILITIES",
    0x4000: "WARN__SURFACE_REFRACTIVITY",
}


def decode_itm_warning_flags(
    warning_flags: int,
) -> tuple[str, ...]:
    """Decode NTIA ITM warning bit flags.

    ITM warnings are bitwise flags, so multiple warning conditions
    may be present in one integer value.

    Unknown bits are retained explicitly so warning information
    is never silently discarded.
    """

    if warning_flags < 0:
        raise ValueError(
            "warning_flags must be zero or greater; "
            f"got {warning_flags}."
        )

    if warning_flags == 0:
        return ()

    warnings: list[str] = []

    known_mask = 0

    for flag, warning_name in (
        ITM_WARNING_FLAGS.items()
    ):
        known_mask |= flag

        if warning_flags & flag:
            warnings.append(
                warning_name
            )

    unknown_bits = (
        warning_flags
        & ~known_mask
    )

    if unknown_bits:
        warnings.append(
            "UNKNOWN_ITM_WARNING_BITS_"
            f"0x{unknown_bits:04X}"
        )

    return tuple(
        warnings
    )


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

        if native_result.return_code not in (
            0,
            1,
        ):
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

        warnings = decode_itm_warning_flags(
            native_result.warning_flags
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
            "itm_warning_names": (
                warnings
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