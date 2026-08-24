"""Free-space RF calculations used for GeoVaris development testing.

This module is intentionally simple.

It does not account for:
- terrain
- clutter
- diffraction
- Earth curvature
- atmospheric refraction
- antenna patterns
- Fresnel clearance
- interference

It must not be treated as a production coverage model.
"""

from __future__ import annotations

import math


def watts_to_dbm(power_watts: float) -> float:
    """Convert watts to dBm."""
    if power_watts <= 0:
        raise ValueError("Power must be greater than zero.")

    return 10.0 * math.log10(power_watts * 1000.0)


def free_space_path_loss_db(
    frequency_mhz: float,
    distance_m: float,
) -> float:
    """Calculate free-space path loss in dB."""

    if frequency_mhz <= 0:
        raise ValueError("Frequency must be greater than zero.")

    if distance_m <= 0:
        raise ValueError("Distance must be greater than zero.")

    distance_km = distance_m / 1000.0

    return (
        32.44
        + 20.0 * math.log10(distance_km)
        + 20.0 * math.log10(frequency_mhz)
    )


def received_power_dbm(
    frequency_mhz: float,
    distance_m: float,
    eirp_watts: float,
) -> float:
    """Estimate received power using free-space path loss."""

    eirp_dbm = watts_to_dbm(eirp_watts)

    path_loss_db = free_space_path_loss_db(
        frequency_mhz=frequency_mhz,
        distance_m=distance_m,
    )

    return eirp_dbm - path_loss_db


def maximum_free_space_distance_m(
    frequency_mhz: float,
    eirp_watts: float,
    receiver_threshold_dbm: float,
) -> float:
    """Calculate distance where received power reaches threshold."""

    if frequency_mhz <= 0:
        raise ValueError("Frequency must be greater than zero.")

    eirp_dbm = watts_to_dbm(eirp_watts)

    allowable_path_loss_db = (
        eirp_dbm - receiver_threshold_dbm
    )

    frequency_term = (
        20.0 * math.log10(frequency_mhz)
    )

    distance_km = 10.0 ** (
        (
            allowable_path_loss_db
            - 32.44
            - frequency_term
        )
        / 20.0
    )

    return distance_km * 1000.0


def estimated_coverage_radius_m(
    frequency_mhz: float,
    eirp_watts: float,
    receiver_threshold_dbm: float,
    calculation_radius_m: float,
) -> float:
    """Return development-test coverage radius."""

    if calculation_radius_m <= 0:
        raise ValueError(
            "Calculation radius must be greater than zero."
        )

    threshold_distance_m = (
        maximum_free_space_distance_m(
            frequency_mhz=frequency_mhz,
            eirp_watts=eirp_watts,
            receiver_threshold_dbm=receiver_threshold_dbm,
        )
    )

    return min(
        threshold_distance_m,
        calculation_radius_m,
    )