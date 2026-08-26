"""Terrain-path engineering analysis for GeoVaris Coverage Intelligence.

This module analyzes an already-sampled terrain profile.

Current scope:
- Transmitter antenna elevation AMSL.
- Receiver antenna elevation AMSL.
- Straight geometric line-of-sight height.
- Effective-Earth-radius curvature adjustment.
- Terrain clearance.
- First Fresnel-zone radius.
- 60 percent first-Fresnel clearance.
- Worst interior terrain and Fresnel obstructions.

Important:
This module does NOT calculate RF propagation loss or predicted service.

This implementation does NOT yet calculate:
- Diffraction loss.
- Clutter loss.
- Atmospheric variability beyond an explicit effective-Earth k-factor.
- Longley-Rice / ITM propagation.

Those belong in later terrain-aware propagation processing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from geovaris_rf.terrain_profile import (
    TerrainProfile,
    TerrainProfileSample,
)


SPEED_OF_LIGHT_M_S = 299_792_458.0

MEAN_EARTH_RADIUS_M = 6_371_008.8

MIN_SUPPORTED_FREQUENCY_MHZ = 600.0
MAX_SUPPORTED_FREQUENCY_MHZ = 6000.0

DEFAULT_K_FACTOR = 4.0 / 3.0


@dataclass(frozen=True)
class TerrainPathAnalysisSample:
    """Engineering geometry for one terrain-profile sample."""

    sample_index: int
    distance_m: float

    terrain_elevation_m: float
    los_elevation_m: float

    earth_curvature_bulge_m: float
    effective_terrain_elevation_m: float

    geometric_terrain_clearance_m: float
    curvature_adjusted_terrain_clearance_m: float

    first_fresnel_radius_m: float

    geometric_first_fresnel_clearance_m: float
    curvature_adjusted_first_fresnel_clearance_m: float

    sixty_percent_fresnel_radius_m: float

    geometric_sixty_percent_fresnel_clearance_m: float
    curvature_adjusted_sixty_percent_fresnel_clearance_m: float


@dataclass(frozen=True)
class TerrainPathAnalysis:
    """LOS, curvature, and Fresnel analysis for one terrain path."""

    frequency_mhz: float
    wavelength_m: float

    earth_radius_m: float
    k_factor: float
    effective_earth_radius_m: float

    transmitter_ground_elevation_m: float
    transmitter_height_agl_m: float
    transmitter_antenna_elevation_m: float

    receiver_ground_elevation_m: float
    receiver_height_agl_m: float
    receiver_antenna_elevation_m: float

    total_distance_m: float

    geometric_los_clear: bool
    curvature_adjusted_los_clear: bool

    geometric_first_fresnel_clear: bool
    curvature_adjusted_first_fresnel_clear: bool

    geometric_sixty_percent_fresnel_clear: bool
    curvature_adjusted_sixty_percent_fresnel_clear: bool

    minimum_geometric_terrain_clearance_m: float
    minimum_curvature_adjusted_terrain_clearance_m: float

    minimum_geometric_first_fresnel_clearance_m: float
    minimum_curvature_adjusted_first_fresnel_clearance_m: float

    minimum_geometric_sixty_percent_fresnel_clearance_m: float
    minimum_curvature_adjusted_sixty_percent_fresnel_clearance_m: float

    worst_geometric_terrain_sample_index: int
    worst_curvature_terrain_sample_index: int
    worst_geometric_fresnel_sample_index: int
    worst_curvature_fresnel_sample_index: int

    samples: tuple[TerrainPathAnalysisSample, ...]


def _validate_frequency(
    frequency_mhz: float,
) -> None:
    """Validate frequency against the GeoVaris supported RF range."""

    if (
        frequency_mhz < MIN_SUPPORTED_FREQUENCY_MHZ
        or frequency_mhz > MAX_SUPPORTED_FREQUENCY_MHZ
    ):
        raise ValueError(
            "frequency_mhz must be between "
            f"{MIN_SUPPORTED_FREQUENCY_MHZ:g} and "
            f"{MAX_SUPPORTED_FREQUENCY_MHZ:g} MHz; "
            f"got {frequency_mhz}."
        )


def _validate_antenna_height(
    value_m: float,
    field_name: str,
) -> None:
    """Validate an antenna/receiver height above ground."""

    if value_m < 0:
        raise ValueError(
            f"{field_name} must be zero or greater; "
            f"got {value_m}."
        )


def _validate_k_factor(
    k_factor: float,
) -> None:
    """Validate the effective-Earth-radius multiplier."""

    if not math.isfinite(k_factor):
        raise ValueError(
            f"k_factor must be finite; got {k_factor}."
        )

    if k_factor <= 0:
        raise ValueError(
            f"k_factor must be greater than zero; got {k_factor}."
        )


def calculate_wavelength_m(
    frequency_mhz: float,
) -> float:
    """Calculate wavelength in meters."""

    _validate_frequency(
        frequency_mhz
    )

    frequency_hz = (
        frequency_mhz
        * 1_000_000.0
    )

    return (
        SPEED_OF_LIGHT_M_S
        / frequency_hz
    )


def calculate_first_fresnel_radius_m(
    frequency_mhz: float,
    distance_from_tx_m: float,
    distance_to_rx_m: float,
) -> float:
    """Calculate first Fresnel-zone radius at one path location."""

    wavelength_m = calculate_wavelength_m(
        frequency_mhz
    )

    if distance_from_tx_m < 0:
        raise ValueError(
            "distance_from_tx_m must be zero or greater; "
            f"got {distance_from_tx_m}."
        )

    if distance_to_rx_m < 0:
        raise ValueError(
            "distance_to_rx_m must be zero or greater; "
            f"got {distance_to_rx_m}."
        )

    total_distance_m = (
        distance_from_tx_m
        + distance_to_rx_m
    )

    if total_distance_m == 0:
        return 0.0

    return math.sqrt(
        wavelength_m
        * distance_from_tx_m
        * distance_to_rx_m
        / total_distance_m
    )


def calculate_earth_curvature_bulge_m(
    distance_from_tx_m: float,
    distance_to_rx_m: float,
    k_factor: float = DEFAULT_K_FACTOR,
    earth_radius_m: float = MEAN_EARTH_RADIUS_M,
) -> float:
    """Calculate effective-Earth curvature bulge above the path chord.

    For local terrestrial RF paths, the standard parabolic
    approximation is:

        bulge = d1 * d2 / (2 * effective_earth_radius)

        effective_earth_radius = earth_radius * k_factor

    A larger k-factor reduces the apparent curvature.

    The bulge is zero at both path endpoints.
    """

    if distance_from_tx_m < 0:
        raise ValueError(
            "distance_from_tx_m must be zero or greater; "
            f"got {distance_from_tx_m}."
        )

    if distance_to_rx_m < 0:
        raise ValueError(
            "distance_to_rx_m must be zero or greater; "
            f"got {distance_to_rx_m}."
        )

    _validate_k_factor(
        k_factor
    )

    if not math.isfinite(earth_radius_m):
        raise ValueError(
            f"earth_radius_m must be finite; got {earth_radius_m}."
        )

    if earth_radius_m <= 0:
        raise ValueError(
            "earth_radius_m must be greater than zero; "
            f"got {earth_radius_m}."
        )

    effective_earth_radius_m = (
        earth_radius_m
        * k_factor
    )

    return (
        distance_from_tx_m
        * distance_to_rx_m
        / (
            2.0
            * effective_earth_radius_m
        )
    )


def _validate_profile(
    profile: TerrainProfile,
) -> None:
    """Validate that a terrain profile can be analyzed."""

    if len(profile.samples) == 0:
        raise ValueError(
            "Terrain profile must contain at least one sample."
        )

    if profile.total_distance_m < 0:
        raise ValueError(
            "Terrain profile total_distance_m cannot be negative."
        )

    previous_distance_m = -1.0

    for sample in profile.samples:
        if sample.distance_m < 0:
            raise ValueError(
                "Terrain profile contains a negative sample distance."
            )

        if sample.distance_m < previous_distance_m:
            raise ValueError(
                "Terrain profile samples must be ordered "
                "by increasing distance."
            )

        previous_distance_m = (
            sample.distance_m
        )


def _obstruction_samples(
    samples: list[TerrainPathAnalysisSample],
) -> list[TerrainPathAnalysisSample]:
    """Return samples suitable for obstruction ranking.

    TX and RX endpoints are not terrain obstructions. When a profile
    has at least three samples, only interior samples are used for
    minimum-clearance and worst-obstruction reporting.

    Very short profiles with fewer than three samples fall back to all
    available samples.
    """

    if len(samples) >= 3:
        return samples[1:-1]

    return samples


def analyze_terrain_path(
    profile: TerrainProfile,
    frequency_mhz: float,
    transmitter_height_agl_m: float,
    receiver_height_agl_m: float,
    k_factor: float = DEFAULT_K_FACTOR,
    earth_radius_m: float = MEAN_EARTH_RADIUS_M,
) -> TerrainPathAnalysis:
    """Analyze geometric and curvature-adjusted path clearance.

    Heights are meters above local ground level.

    The effective-Earth-radius method represents a configurable
    atmospheric-refraction assumption through k_factor.

    This is still path geometry, not a complete RF propagation model.
    """

    _validate_profile(
        profile
    )

    _validate_frequency(
        frequency_mhz
    )

    _validate_antenna_height(
        transmitter_height_agl_m,
        "transmitter_height_agl_m",
    )

    _validate_antenna_height(
        receiver_height_agl_m,
        "receiver_height_agl_m",
    )

    _validate_k_factor(
        k_factor
    )

    if not math.isfinite(earth_radius_m):
        raise ValueError(
            f"earth_radius_m must be finite; got {earth_radius_m}."
        )

    if earth_radius_m <= 0:
        raise ValueError(
            "earth_radius_m must be greater than zero; "
            f"got {earth_radius_m}."
        )

    wavelength_m = calculate_wavelength_m(
        frequency_mhz
    )

    effective_earth_radius_m = (
        earth_radius_m
        * k_factor
    )

    first_profile_sample: TerrainProfileSample = (
        profile.samples[0]
    )

    last_profile_sample: TerrainProfileSample = (
        profile.samples[-1]
    )

    transmitter_ground_elevation_m = (
        first_profile_sample.elevation_m
    )

    receiver_ground_elevation_m = (
        last_profile_sample.elevation_m
    )

    transmitter_antenna_elevation_m = (
        transmitter_ground_elevation_m
        + transmitter_height_agl_m
    )

    receiver_antenna_elevation_m = (
        receiver_ground_elevation_m
        + receiver_height_agl_m
    )

    total_distance_m = (
        profile.total_distance_m
    )

    analysis_samples: list[
        TerrainPathAnalysisSample
    ] = []

    for index, sample in enumerate(
        profile.samples
    ):
        if total_distance_m == 0:
            path_fraction = 0.0
        else:
            path_fraction = (
                sample.distance_m
                / total_distance_m
            )

        los_elevation_m = (
            transmitter_antenna_elevation_m
            + path_fraction
            * (
                receiver_antenna_elevation_m
                - transmitter_antenna_elevation_m
            )
        )

        geometric_terrain_clearance_m = (
            los_elevation_m
            - sample.elevation_m
        )

        distance_from_tx_m = (
            sample.distance_m
        )

        distance_to_rx_m = max(
            0.0,
            total_distance_m
            - sample.distance_m,
        )

        earth_curvature_bulge_m = (
            calculate_earth_curvature_bulge_m(
                distance_from_tx_m=distance_from_tx_m,
                distance_to_rx_m=distance_to_rx_m,
                k_factor=k_factor,
                earth_radius_m=earth_radius_m,
            )
        )

        effective_terrain_elevation_m = (
            sample.elevation_m
            + earth_curvature_bulge_m
        )

        curvature_adjusted_terrain_clearance_m = (
            los_elevation_m
            - effective_terrain_elevation_m
        )

        first_fresnel_radius_m = (
            calculate_first_fresnel_radius_m(
                frequency_mhz=frequency_mhz,
                distance_from_tx_m=distance_from_tx_m,
                distance_to_rx_m=distance_to_rx_m,
            )
        )

        geometric_first_fresnel_clearance_m = (
            geometric_terrain_clearance_m
            - first_fresnel_radius_m
        )

        curvature_adjusted_first_fresnel_clearance_m = (
            curvature_adjusted_terrain_clearance_m
            - first_fresnel_radius_m
        )

        sixty_percent_fresnel_radius_m = (
            first_fresnel_radius_m
            * 0.60
        )

        geometric_sixty_percent_fresnel_clearance_m = (
            geometric_terrain_clearance_m
            - sixty_percent_fresnel_radius_m
        )

        curvature_adjusted_sixty_percent_fresnel_clearance_m = (
            curvature_adjusted_terrain_clearance_m
            - sixty_percent_fresnel_radius_m
        )

        analysis_samples.append(
            TerrainPathAnalysisSample(
                sample_index=index,
                distance_m=sample.distance_m,
                terrain_elevation_m=sample.elevation_m,
                los_elevation_m=los_elevation_m,
                earth_curvature_bulge_m=(
                    earth_curvature_bulge_m
                ),
                effective_terrain_elevation_m=(
                    effective_terrain_elevation_m
                ),
                geometric_terrain_clearance_m=(
                    geometric_terrain_clearance_m
                ),
                curvature_adjusted_terrain_clearance_m=(
                    curvature_adjusted_terrain_clearance_m
                ),
                first_fresnel_radius_m=(
                    first_fresnel_radius_m
                ),
                geometric_first_fresnel_clearance_m=(
                    geometric_first_fresnel_clearance_m
                ),
                curvature_adjusted_first_fresnel_clearance_m=(
                    curvature_adjusted_first_fresnel_clearance_m
                ),
                sixty_percent_fresnel_radius_m=(
                    sixty_percent_fresnel_radius_m
                ),
                geometric_sixty_percent_fresnel_clearance_m=(
                    geometric_sixty_percent_fresnel_clearance_m
                ),
                curvature_adjusted_sixty_percent_fresnel_clearance_m=(
                    curvature_adjusted_sixty_percent_fresnel_clearance_m
                ),
            )
        )

    ranked_samples = _obstruction_samples(
        analysis_samples
    )

    worst_geometric_terrain_sample = min(
        ranked_samples,
        key=lambda sample: (
            sample.geometric_terrain_clearance_m
        ),
    )

    worst_curvature_terrain_sample = min(
        ranked_samples,
        key=lambda sample: (
            sample.curvature_adjusted_terrain_clearance_m
        ),
    )

    worst_geometric_fresnel_sample = min(
        ranked_samples,
        key=lambda sample: (
            sample.geometric_first_fresnel_clearance_m
        ),
    )

    worst_curvature_fresnel_sample = min(
        ranked_samples,
        key=lambda sample: (
            sample.curvature_adjusted_first_fresnel_clearance_m
        ),
    )

    worst_geometric_sixty_percent_sample = min(
        ranked_samples,
        key=lambda sample: (
            sample.geometric_sixty_percent_fresnel_clearance_m
        ),
    )

    worst_curvature_sixty_percent_sample = min(
        ranked_samples,
        key=lambda sample: (
            sample.curvature_adjusted_sixty_percent_fresnel_clearance_m
        ),
    )

    minimum_geometric_terrain_clearance_m = (
        worst_geometric_terrain_sample
        .geometric_terrain_clearance_m
    )

    minimum_curvature_adjusted_terrain_clearance_m = (
        worst_curvature_terrain_sample
        .curvature_adjusted_terrain_clearance_m
    )

    minimum_geometric_first_fresnel_clearance_m = (
        worst_geometric_fresnel_sample
        .geometric_first_fresnel_clearance_m
    )

    minimum_curvature_adjusted_first_fresnel_clearance_m = (
        worst_curvature_fresnel_sample
        .curvature_adjusted_first_fresnel_clearance_m
    )

    minimum_geometric_sixty_percent_fresnel_clearance_m = (
        worst_geometric_sixty_percent_sample
        .geometric_sixty_percent_fresnel_clearance_m
    )

    minimum_curvature_adjusted_sixty_percent_fresnel_clearance_m = (
        worst_curvature_sixty_percent_sample
        .curvature_adjusted_sixty_percent_fresnel_clearance_m
    )

    return TerrainPathAnalysis(
        frequency_mhz=frequency_mhz,
        wavelength_m=wavelength_m,
        earth_radius_m=earth_radius_m,
        k_factor=k_factor,
        effective_earth_radius_m=effective_earth_radius_m,
        transmitter_ground_elevation_m=(
            transmitter_ground_elevation_m
        ),
        transmitter_height_agl_m=(
            transmitter_height_agl_m
        ),
        transmitter_antenna_elevation_m=(
            transmitter_antenna_elevation_m
        ),
        receiver_ground_elevation_m=(
            receiver_ground_elevation_m
        ),
        receiver_height_agl_m=(
            receiver_height_agl_m
        ),
        receiver_antenna_elevation_m=(
            receiver_antenna_elevation_m
        ),
        total_distance_m=total_distance_m,
        geometric_los_clear=(
            minimum_geometric_terrain_clearance_m
            >= 0.0
        ),
        curvature_adjusted_los_clear=(
            minimum_curvature_adjusted_terrain_clearance_m
            >= 0.0
        ),
        geometric_first_fresnel_clear=(
            minimum_geometric_first_fresnel_clearance_m
            >= 0.0
        ),
        curvature_adjusted_first_fresnel_clear=(
            minimum_curvature_adjusted_first_fresnel_clearance_m
            >= 0.0
        ),
        geometric_sixty_percent_fresnel_clear=(
            minimum_geometric_sixty_percent_fresnel_clearance_m
            >= 0.0
        ),
        curvature_adjusted_sixty_percent_fresnel_clear=(
            minimum_curvature_adjusted_sixty_percent_fresnel_clearance_m
            >= 0.0
        ),
        minimum_geometric_terrain_clearance_m=(
            minimum_geometric_terrain_clearance_m
        ),
        minimum_curvature_adjusted_terrain_clearance_m=(
            minimum_curvature_adjusted_terrain_clearance_m
        ),
        minimum_geometric_first_fresnel_clearance_m=(
            minimum_geometric_first_fresnel_clearance_m
        ),
        minimum_curvature_adjusted_first_fresnel_clearance_m=(
            minimum_curvature_adjusted_first_fresnel_clearance_m
        ),
        minimum_geometric_sixty_percent_fresnel_clearance_m=(
            minimum_geometric_sixty_percent_fresnel_clearance_m
        ),
        minimum_curvature_adjusted_sixty_percent_fresnel_clearance_m=(
            minimum_curvature_adjusted_sixty_percent_fresnel_clearance_m
        ),
        worst_geometric_terrain_sample_index=(
            worst_geometric_terrain_sample.sample_index
        ),
        worst_curvature_terrain_sample_index=(
            worst_curvature_terrain_sample.sample_index
        ),
        worst_geometric_fresnel_sample_index=(
            worst_geometric_fresnel_sample.sample_index
        ),
        worst_curvature_fresnel_sample_index=(
            worst_curvature_fresnel_sample.sample_index
        ),
        samples=tuple(
            analysis_samples
        ),
    )