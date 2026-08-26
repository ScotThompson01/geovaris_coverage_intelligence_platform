"""Native NTIA ITM DLL adapter for GeoVaris Coverage Intelligence.

This module is the low-level ctypes boundary between Python and the
official NTIA ITM Windows DLL.

Current scope:
- Load itm.dll.
- Bind ITM_P2P_CR_Ex.
- Execute one point-to-point confidence/reliability calculation.
- Return basic transmission loss, warnings, return code, and
  intermediate engineering values.

This module does not decide whether a location is "covered".
ITM produces an engineering propagation-loss estimate.
"""

from __future__ import annotations

import ctypes
import math
from dataclasses import dataclass
from pathlib import Path

from geovaris_rf.itm import ItmNativeInput


@dataclass(frozen=True)
class ItmIntermediateValues:
    """Intermediate values returned by NTIA ITM."""

    theta_hzn_tx_rad: float
    theta_hzn_rx_rad: float

    distance_horizon_tx_m: float
    distance_horizon_rx_m: float

    effective_height_tx_m: float
    effective_height_rx_m: float

    surface_refractivity_n_units: float
    terrain_irregularity_m: float

    reference_attenuation_db: float
    free_space_loss_db: float

    path_distance_km: float

    propagation_mode: int


@dataclass(frozen=True)
class ItmNativeResult:
    """Result returned by the native NTIA ITM adapter."""

    return_code: int
    warning_flags: int

    basic_transmission_loss_db: float

    intermediate: ItmIntermediateValues


class _CIntermediateValues(
    ctypes.Structure
):
    """ctypes mirror of NTIA IntermediateValues."""

    _fields_ = [
        (
            "theta_hzn",
            ctypes.c_double * 2,
        ),
        (
            "d_hzn__meter",
            ctypes.c_double * 2,
        ),
        (
            "h_e__meter",
            ctypes.c_double * 2,
        ),
        (
            "N_s",
            ctypes.c_double,
        ),
        (
            "delta_h__meter",
            ctypes.c_double,
        ),
        (
            "A_ref__db",
            ctypes.c_double,
        ),
        (
            "A_fs__db",
            ctypes.c_double,
        ),
        (
            "d__km",
            ctypes.c_double,
        ),
        (
            "mode",
            ctypes.c_int,
        ),
    ]


class ItmNativeLibrary:
    """Loaded NTIA ITM native library."""

    def __init__(
        self,
        dll_path: str,
    ) -> None:
        path = Path(
            dll_path
        )

        if not path.exists():
            raise FileNotFoundError(
                f"NTIA ITM DLL does not exist: {dll_path}"
            )

        if not path.is_file():
            raise ValueError(
                f"NTIA ITM DLL path is not a file: {dll_path}"
            )

        self.dll_path = str(
            path.resolve()
        )

        try:
            # NTIA exports these functions using extern "C".
            # The DLL uses the standard C calling convention.
            self._dll = ctypes.CDLL(
                self.dll_path
            )

        except OSError as exc:
            raise RuntimeError(
                "Unable to load NTIA ITM DLL. "
                f"Path: {self.dll_path}. "
                f"Original error: {exc}"
            ) from exc

        try:
            self._p2p_cr_ex = (
                self._dll.ITM_P2P_CR_Ex
            )

        except AttributeError as exc:
            raise RuntimeError(
                "Loaded DLL does not export ITM_P2P_CR_Ex. "
                f"Path: {self.dll_path}"
            ) from exc

        self._configure_function_signature()

    def _configure_function_signature(
        self,
    ) -> None:
        """Configure ctypes argument and return types."""

        self._p2p_cr_ex.argtypes = [
            # h_tx__meter
            ctypes.c_double,

            # h_rx__meter
            ctypes.c_double,

            # pfl[]
            ctypes.POINTER(
                ctypes.c_double
            ),

            # climate
            ctypes.c_int,

            # N_0
            ctypes.c_double,

            # f__mhz
            ctypes.c_double,

            # pol
            ctypes.c_int,

            # epsilon
            ctypes.c_double,

            # sigma
            ctypes.c_double,

            # mdvar
            ctypes.c_int,

            # confidence
            ctypes.c_double,

            # reliability
            ctypes.c_double,

            # A__db
            ctypes.POINTER(
                ctypes.c_double
            ),

            # warnings
            ctypes.POINTER(
                ctypes.c_long
            ),

            # IntermediateValues
            ctypes.POINTER(
                _CIntermediateValues
            ),
        ]

        self._p2p_cr_ex.restype = (
            ctypes.c_int
        )

    def calculate_p2p_cr(
        self,
        native_input: ItmNativeInput,
    ) -> ItmNativeResult:
        """Execute NTIA ITM P2P confidence/reliability mode."""

        if len(
            native_input.pfl
        ) < 4:
            raise ValueError(
                "ITM native PFL must contain at least "
                "two header values and two elevations."
            )

        interval_count = int(
            native_input.pfl[0]
        )

        elevation_count = (
            len(native_input.pfl)
            - 2
        )

        if interval_count + 1 != elevation_count:
            raise ValueError(
                "ITM PFL interval/elevation count mismatch. "
                f"Intervals={interval_count}, "
                f"elevations={elevation_count}."
            )

        if (
            not math.isfinite(
                native_input.pfl[1]
            )
            or native_input.pfl[1] <= 0.0
        ):
            raise ValueError(
                "ITM PFL spacing must be finite "
                "and greater than zero."
            )

        pfl_type = (
            ctypes.c_double
            * len(
                native_input.pfl
            )
        )

        pfl_array = pfl_type(
            *native_input.pfl
        )

        loss_db = ctypes.c_double(
            0.0
        )

        warnings = ctypes.c_long(
            0
        )

        intermediate = (
            _CIntermediateValues()
        )

        return_code = int(
            self._p2p_cr_ex(
                native_input.transmitter_height_m,
                native_input.receiver_height_m,
                pfl_array,
                native_input.climate,
                native_input.surface_refractivity_n_units,
                native_input.frequency_mhz,
                native_input.polarization,
                native_input.ground_dielectric_constant,
                native_input.ground_conductivity_s_per_m,
                native_input.variability_mode,
                native_input.confidence_percent,
                native_input.reliability_percent,
                ctypes.byref(
                    loss_db
                ),
                ctypes.byref(
                    warnings
                ),
                ctypes.byref(
                    intermediate
                ),
            )
        )

        if not math.isfinite(
            loss_db.value
        ):
            raise RuntimeError(
                "NTIA ITM returned a non-finite "
                "basic transmission loss."
            )

        result = ItmNativeResult(
            return_code=return_code,
            warning_flags=int(
                warnings.value
            ),
            basic_transmission_loss_db=float(
                loss_db.value
            ),
            intermediate=(
                ItmIntermediateValues(
                    theta_hzn_tx_rad=float(
                        intermediate.theta_hzn[0]
                    ),
                    theta_hzn_rx_rad=float(
                        intermediate.theta_hzn[1]
                    ),
                    distance_horizon_tx_m=float(
                        intermediate.d_hzn__meter[0]
                    ),
                    distance_horizon_rx_m=float(
                        intermediate.d_hzn__meter[1]
                    ),
                    effective_height_tx_m=float(
                        intermediate.h_e__meter[0]
                    ),
                    effective_height_rx_m=float(
                        intermediate.h_e__meter[1]
                    ),
                    surface_refractivity_n_units=float(
                        intermediate.N_s
                    ),
                    terrain_irregularity_m=float(
                        intermediate.delta_h__meter
                    ),
                    reference_attenuation_db=float(
                        intermediate.A_ref__db
                    ),
                    free_space_loss_db=float(
                        intermediate.A_fs__db
                    ),
                    path_distance_km=float(
                        intermediate.d__km
                    ),
                    propagation_mode=int(
                        intermediate.mode
                    ),
                )
            ),
        )

        return result