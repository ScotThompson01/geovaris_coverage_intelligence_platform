"""Free-space RF calculations for GeoVaris Coverage Intelligence.

This module provides the free-space link-budget calculations used by the
Rapid Coverage Estimate methodology.

The free-space calculation establishes the maximum theoretical distance
allowed by the configured RF link budget. It does not determine whether
terrain or clutter blocks the path.

Rapid Coverage Estimate processing will later intersect this maximum
free-space range with a terrain/clutter line-of-sight viewshed.

This module does not account for:
- terrain
- clutter obstruction
- diffraction
- Earth curvature
- atmospheric refraction
- antenna radiation patterns
- Fresnel-zone clearance
- interference

Those effects must be handled separately where applicable.

RF results are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


FSPL_REFERENCE_DB = 32.44


@dataclass(frozen=True)
class FreeSpaceRangeResult:
    """Result of a free-space maximum-range link-budget calculation."""

    frequency_mhz: float
    eirp_dbm: float
    receiver_gain_dbi: float
    additional_losses_db: float
    receiver_threshold_dbm: float
    maximum_path_loss_db: float
    maximum_distance_m: float


def _validate_finite(
    value: float,
    *,
    name: str,
) -> float:
    """Validate that an RF input is finite."""

    numeric_value = float(value)

    if not math.isfinite(
        numeric_value
    ):
        raise ValueError(
            f"{name} must be a finite value."
        )

    return numeric_value


def watts_to_dbm(
    power_watts: float,
) -> float:
    """Convert watts to dBm."""

    power_watts = _validate_finite(
        power_watts,
        name="Power",
    )

    if power_watts <= 0:
        raise ValueError(
            "Power must be greater than zero."
        )

    return (
        10.0
        * math.log10(
            power_watts * 1000.0
        )
    )


def free_space_path_loss_db(
    frequency_mhz: float,
    distance_m: float,
) -> float:
    """Calculate free-space path loss in dB.

    Uses frequency in MHz and distance in kilometers:

        FSPL(dB) =
            32.44
            + 20 log10(distance_km)
            + 20 log10(frequency_mhz)
    """

    frequency_mhz = _validate_finite(
        frequency_mhz,
        name="Frequency",
    )

    distance_m = _validate_finite(
        distance_m,
        name="Distance",
    )

    if frequency_mhz <= 0:
        raise ValueError(
            "Frequency must be greater than zero."
        )

    if distance_m <= 0:
        raise ValueError(
            "Distance must be greater than zero."
        )

    distance_km = (
        distance_m
        / 1000.0
    )

    return (
        FSPL_REFERENCE_DB
        + 20.0
        * math.log10(
            distance_km
        )
        + 20.0
        * math.log10(
            frequency_mhz
        )
    )


def received_power_dbm(
    frequency_mhz: float,
    distance_m: float,
    eirp_watts: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> float:
    """Estimate received power using free-space path loss.

    EIRP already includes transmitter antenna gain, so transmitter gain
    must not be added again.

    Received power is:

        EIRP
        + receiver gain
        - free-space path loss
        - additional losses
    """

    receiver_gain_dbi = _validate_finite(
        receiver_gain_dbi,
        name="Receiver gain",
    )

    additional_losses_db = _validate_finite(
        additional_losses_db,
        name="Additional losses",
    )

    if additional_losses_db < 0:
        raise ValueError(
            "Additional losses must be greater than "
            "or equal to zero."
        )

    eirp_dbm = watts_to_dbm(
        eirp_watts
    )

    path_loss_db = (
        free_space_path_loss_db(
            frequency_mhz=(
                frequency_mhz
            ),
            distance_m=(
                distance_m
            ),
        )
    )

    return (
        eirp_dbm
        + receiver_gain_dbi
        - path_loss_db
        - additional_losses_db
    )


def maximum_allowable_path_loss_db(
    *,
    eirp_dbm: float,
    receiver_threshold_dbm: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> float:
    """Calculate the maximum allowable propagation loss.

    Link budget:

        received =
            EIRP
            + receiver gain
            - propagation loss
            - additional losses

    At the receiver threshold:

        maximum propagation loss =
            EIRP
            + receiver gain
            - additional losses
            - receiver threshold
    """

    eirp_dbm = _validate_finite(
        eirp_dbm,
        name="EIRP",
    )

    receiver_threshold_dbm = (
        _validate_finite(
            receiver_threshold_dbm,
            name="Receiver threshold",
        )
    )

    receiver_gain_dbi = _validate_finite(
        receiver_gain_dbi,
        name="Receiver gain",
    )

    additional_losses_db = (
        _validate_finite(
            additional_losses_db,
            name="Additional losses",
        )
    )

    if additional_losses_db < 0:
        raise ValueError(
            "Additional losses must be greater than "
            "or equal to zero."
        )

    return (
        eirp_dbm
        + receiver_gain_dbi
        - additional_losses_db
        - receiver_threshold_dbm
    )


def calculate_free_space_range(
    *,
    frequency_mhz: float,
    eirp_dbm: float,
    receiver_threshold_dbm: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> FreeSpaceRangeResult:
    """Calculate maximum free-space distance for a link budget.

    This is the primary free-space range function for the GeoVaris
    Rapid Coverage Estimate methodology.

    The returned distance is a theoretical free-space limit. Terrain,
    clutter, Earth curvature, and other visibility constraints must be
    evaluated separately.
    """

    frequency_mhz = _validate_finite(
        frequency_mhz,
        name="Frequency",
    )

    if frequency_mhz <= 0:
        raise ValueError(
            "Frequency must be greater than zero."
        )

    eirp_dbm = _validate_finite(
        eirp_dbm,
        name="EIRP",
    )

    receiver_threshold_dbm = (
        _validate_finite(
            receiver_threshold_dbm,
            name="Receiver threshold",
        )
    )

    receiver_gain_dbi = _validate_finite(
        receiver_gain_dbi,
        name="Receiver gain",
    )

    additional_losses_db = (
        _validate_finite(
            additional_losses_db,
            name="Additional losses",
        )
    )

    maximum_path_loss_db = (
        maximum_allowable_path_loss_db(
            eirp_dbm=eirp_dbm,
            receiver_threshold_dbm=(
                receiver_threshold_dbm
            ),
            receiver_gain_dbi=(
                receiver_gain_dbi
            ),
            additional_losses_db=(
                additional_losses_db
            ),
        )
    )

    frequency_term_db = (
        20.0
        * math.log10(
            frequency_mhz
        )
    )

    distance_km = (
        10.0
        ** (
            (
                maximum_path_loss_db
                - FSPL_REFERENCE_DB
                - frequency_term_db
            )
            / 20.0
        )
    )

    maximum_distance_m = (
        distance_km
        * 1000.0
    )

    if (
        not math.isfinite(
            maximum_distance_m
        )
        or maximum_distance_m <= 0
    ):
        raise ValueError(
            "Calculated free-space distance is invalid."
        )

    return FreeSpaceRangeResult(
        frequency_mhz=frequency_mhz,
        eirp_dbm=eirp_dbm,
        receiver_gain_dbi=(
            receiver_gain_dbi
        ),
        additional_losses_db=(
            additional_losses_db
        ),
        receiver_threshold_dbm=(
            receiver_threshold_dbm
        ),
        maximum_path_loss_db=(
            maximum_path_loss_db
        ),
        maximum_distance_m=(
            maximum_distance_m
        ),
    )


def maximum_free_space_distance_m(
    frequency_mhz: float,
    eirp_watts: float,
    receiver_threshold_dbm: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> float:
    """Calculate maximum free-space distance using EIRP in watts.

    This function is retained for compatibility with existing GeoVaris
    development code.

    New Rapid Coverage Estimate code should normally use
    ``calculate_free_space_range`` so the full calculation result and
    link-budget lineage are available.
    """

    eirp_dbm = watts_to_dbm(
        eirp_watts
    )

    result = (
        calculate_free_space_range(
            frequency_mhz=(
                frequency_mhz
            ),
            eirp_dbm=eirp_dbm,
            receiver_threshold_dbm=(
                receiver_threshold_dbm
            ),
            receiver_gain_dbi=(
                receiver_gain_dbi
            ),
            additional_losses_db=(
                additional_losses_db
            ),
        )
    )

    return result.maximum_distance_m


def estimated_coverage_radius_m(
    frequency_mhz: float,
    eirp_watts: float,
    receiver_threshold_dbm: float,
    calculation_radius_m: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> float:
    """Return the lesser of free-space range and calculation radius."""

    calculation_radius_m = (
        _validate_finite(
            calculation_radius_m,
            name="Calculation radius",
        )
    )

    if calculation_radius_m <= 0:
        raise ValueError(
            "Calculation radius must be greater than zero."
        )

    threshold_distance_m = (
        maximum_free_space_distance_m(
            frequency_mhz=(
                frequency_mhz
            ),
            eirp_watts=(
                eirp_watts
            ),
            receiver_threshold_dbm=(
                receiver_threshold_dbm
            ),
            receiver_gain_dbi=(
                receiver_gain_dbi
            ),
            additional_losses_db=(
                additional_losses_db
            ),
        )
    )

    return min(
        threshold_distance_m,
        calculation_radius_m,
    )