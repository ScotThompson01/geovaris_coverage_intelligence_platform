"""GeoVaris ITM configuration and native-input preparation.

This module defines GeoVaris-owned structures for preparing inputs for
the NTIA Irregular Terrain Model (ITM / Longley-Rice).

It intentionally does NOT invoke the native NTIA library yet.

Responsibilities:
- Validate GeoVaris ITM engineering assumptions.
- Preserve explicit variability assumptions.
- Convert GeoVaris 0..1 probability fractions to NTIA percentages.
- Convert terrain profiles to official ITM PFL layout.
- Keep application code independent of the native implementation.

Propagation predictions remain engineering estimates and do not
guarantee service availability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

from geovaris_rf.propagation import (
    PropagationRequest,
)
from geovaris_rf.terrain_profile import (
    TerrainProfile,
)


class ItmClimate(IntEnum):
    """NTIA ITM radio-climate categories."""

    EQUATORIAL = 1
    CONTINENTAL_SUBTROPICAL = 2
    MARITIME_SUBTROPICAL = 3
    DESERT = 4
    CONTINENTAL_TEMPERATE = 5
    MARITIME_TEMPERATE_OVER_LAND = 6
    MARITIME_TEMPERATE_OVER_SEA = 7


class ItmPolarization(IntEnum):
    """NTIA ITM polarization values."""

    HORIZONTAL = 0
    VERTICAL = 1


class ItmVariabilityMode(IntEnum):
    """Base NTIA ITM variability modes.

    NTIA also permits +10 and/or +20 modifiers to disable selected
    location or situation variability behavior. GeoVaris does not
    expose those modifiers yet; they can be added explicitly later.
    """

    SINGLE_MESSAGE = 0
    ACCIDENTAL = 1
    MOBILE = 2
    BROADCAST = 3


@dataclass(frozen=True)
class ItmConfiguration:
    """GeoVaris configuration for ITM confidence/reliability mode.

    confidence and reliability are stored by GeoVaris as fractions:

        0 < value < 1

    The native NTIA adapter converts them to percentages:

        0 < value < 100

    This keeps probability representation consistent inside GeoVaris
    while making the native boundary explicit.
    """

    climate: ItmClimate
    polarization: ItmPolarization
    variability_mode: ItmVariabilityMode

    surface_refractivity_n_units: float
    ground_dielectric_constant: float
    ground_conductivity_s_per_m: float

    confidence: float
    reliability: float

    def __post_init__(self) -> None:
        if not isinstance(
            self.climate,
            ItmClimate,
        ):
            raise ValueError(
                "climate must be an ItmClimate value."
            )

        if not isinstance(
            self.polarization,
            ItmPolarization,
        ):
            raise ValueError(
                "polarization must be an ItmPolarization value."
            )

        if not isinstance(
            self.variability_mode,
            ItmVariabilityMode,
        ):
            raise ValueError(
                "variability_mode must be an "
                "ItmVariabilityMode value."
            )

        if (
            not math.isfinite(
                self.surface_refractivity_n_units
            )
            or self.surface_refractivity_n_units < 250.0
            or self.surface_refractivity_n_units > 400.0
        ):
            raise ValueError(
                "surface_refractivity_n_units must be "
                "between 250 and 400 N-units; got "
                f"{self.surface_refractivity_n_units}."
            )

        if (
            not math.isfinite(
                self.ground_dielectric_constant
            )
            or self.ground_dielectric_constant <= 1.0
        ):
            raise ValueError(
                "ground_dielectric_constant must be finite "
                "and greater than 1; got "
                f"{self.ground_dielectric_constant}."
            )

        if (
            not math.isfinite(
                self.ground_conductivity_s_per_m
            )
            or self.ground_conductivity_s_per_m <= 0.0
        ):
            raise ValueError(
                "ground_conductivity_s_per_m must be finite "
                "and greater than zero; got "
                f"{self.ground_conductivity_s_per_m}."
            )

        for field_name, value in (
            (
                "confidence",
                self.confidence,
            ),
            (
                "reliability",
                self.reliability,
            ),
        ):
            if not math.isfinite(
                value
            ):
                raise ValueError(
                    f"{field_name} must be finite; got {value}."
                )

            if value <= 0.0 or value >= 1.0:
                raise ValueError(
                    f"{field_name} must be greater than 0 "
                    f"and less than 1; got {value}."
                )


@dataclass(frozen=True)
class ItmTerrainProfile:
    """Uniform terrain profile prepared for ITM."""

    sample_spacing_m: float
    elevations_m: tuple[float, ...]

    @property
    def sample_count(self) -> int:
        return len(
            self.elevations_m
        )

    @property
    def interval_count(self) -> int:
        """Number of profile intervals.

        This becomes pfl[0] in the NTIA PFL format.
        """

        return max(
            0,
            self.sample_count - 1,
        )

    @property
    def total_distance_m(self) -> float:
        if self.sample_count < 2:
            return 0.0

        return (
            self.sample_spacing_m
            * self.interval_count
        )

    def to_pfl(self) -> tuple[float, ...]:
        """Return official ITM PFL array layout.

        PFL format:

            pfl[0] = number of elevation intervals
            pfl[1] = uniform spacing in meters
            pfl[2:] = terrain elevations in meters AMSL
        """

        if self.sample_count < 2:
            raise ValueError(
                "ITM PFL requires at least two elevation samples."
            )

        return (
            float(
                self.interval_count
            ),
            float(
                self.sample_spacing_m
            ),
            *self.elevations_m,
        )


@dataclass(frozen=True)
class ItmNativeInput:
    """Inputs in the units/form expected by the NTIA ITM boundary."""

    pfl: tuple[float, ...]

    transmitter_height_m: float
    receiver_height_m: float

    climate: int
    surface_refractivity_n_units: float
    frequency_mhz: float
    polarization: int
    ground_dielectric_constant: float
    ground_conductivity_s_per_m: float

    variability_mode: int

    confidence_percent: float
    reliability_percent: float


@dataclass(frozen=True)
class ItmPreparedRequest:
    """Complete GeoVaris request prepared for native ITM execution."""

    frequency_mhz: float

    transmitter_height_agl_m: float
    receiver_height_agl_m: float

    terrain: ItmTerrainProfile
    configuration: ItmConfiguration

    native_input: ItmNativeInput


def _validate_profile_for_itm(
    profile: TerrainProfile,
) -> None:
    """Validate a terrain profile before ITM conversion."""

    if len(
        profile.samples
    ) < 2:
        raise ValueError(
            "ITM requires at least two terrain-profile samples."
        )

    if (
        not math.isfinite(
            profile.total_distance_m
        )
        or profile.total_distance_m <= 0.0
    ):
        raise ValueError(
            "terrain profile total_distance_m must be finite "
            "and greater than zero."
        )

    previous_distance_m: float | None = None

    for sample in profile.samples:
        if not math.isfinite(
            sample.distance_m
        ):
            raise ValueError(
                "terrain profile contains a non-finite distance."
            )

        if not math.isfinite(
            sample.elevation_m
        ):
            raise ValueError(
                "terrain profile contains a non-finite elevation."
            )

        if previous_distance_m is not None:
            if sample.distance_m <= previous_distance_m:
                raise ValueError(
                    "terrain profile sample distances must "
                    "increase strictly."
                )

        previous_distance_m = (
            sample.distance_m
        )


def terrain_profile_to_itm(
    profile: TerrainProfile,
    spacing_tolerance_m: float = 0.05,
) -> ItmTerrainProfile:
    """Convert a GeoVaris terrain profile to a uniform ITM profile."""

    _validate_profile_for_itm(
        profile
    )

    if (
        not math.isfinite(
            spacing_tolerance_m
        )
        or spacing_tolerance_m < 0.0
    ):
        raise ValueError(
            "spacing_tolerance_m must be finite and zero "
            f"or greater; got {spacing_tolerance_m}."
        )

    nominal_spacing_m = (
        profile.total_distance_m
        / (
            len(profile.samples)
            - 1
        )
    )

    for index in range(
        1,
        len(profile.samples),
    ):
        spacing_m = (
            profile.samples[index].distance_m
            - profile.samples[
                index - 1
            ].distance_m
        )

        if not math.isclose(
            spacing_m,
            nominal_spacing_m,
            rel_tol=0.0,
            abs_tol=spacing_tolerance_m,
        ):
            raise ValueError(
                "Terrain profile is not uniformly sampled enough "
                "for ITM. "
                f"Segment {index - 1} spacing={spacing_m}, "
                f"expected approximately {nominal_spacing_m}."
            )

    elevations_m = tuple(
        float(
            sample.elevation_m
        )
        for sample in profile.samples
    )

    return ItmTerrainProfile(
        sample_spacing_m=nominal_spacing_m,
        elevations_m=elevations_m,
    )


def _validate_native_terminal_height(
    height_m: float,
    field_name: str,
) -> None:
    """Apply NTIA ITM terminal-height limits."""

    if height_m < 0.5 or height_m > 3000.0:
        raise ValueError(
            f"{field_name} must be between 0.5 and "
            f"3000 meters for NTIA ITM; got {height_m}."
        )


def prepare_itm_request(
    request: PropagationRequest,
    configuration: ItmConfiguration,
) -> ItmPreparedRequest:
    """Prepare a GeoVaris request for the native NTIA ITM adapter."""

    _validate_native_terminal_height(
        request.transmitter_height_agl_m,
        "transmitter_height_agl_m",
    )

    _validate_native_terminal_height(
        request.receiver_height_agl_m,
        "receiver_height_agl_m",
    )

    terrain = terrain_profile_to_itm(
        request.terrain_profile
    )

    native_input = ItmNativeInput(
        pfl=terrain.to_pfl(),
        transmitter_height_m=(
            request.transmitter_height_agl_m
        ),
        receiver_height_m=(
            request.receiver_height_agl_m
        ),
        climate=int(
            configuration.climate
        ),
        surface_refractivity_n_units=(
            configuration.surface_refractivity_n_units
        ),
        frequency_mhz=(
            request.frequency_mhz
        ),
        polarization=int(
            configuration.polarization
        ),
        ground_dielectric_constant=(
            configuration.ground_dielectric_constant
        ),
        ground_conductivity_s_per_m=(
            configuration.ground_conductivity_s_per_m
        ),
        variability_mode=int(
            configuration.variability_mode
        ),
        confidence_percent=(
            configuration.confidence
            * 100.0
        ),
        reliability_percent=(
            configuration.reliability
            * 100.0
        ),
    )

    return ItmPreparedRequest(
        frequency_mhz=(
            request.frequency_mhz
        ),
        transmitter_height_agl_m=(
            request.transmitter_height_agl_m
        ),
        receiver_height_agl_m=(
            request.receiver_height_agl_m
        ),
        terrain=terrain,
        configuration=configuration,
        native_input=native_input,
    )