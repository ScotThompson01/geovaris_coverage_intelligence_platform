"""GeoVaris RF link-budget calculations.

This module converts propagation loss into predicted received power
and compares that prediction with a receiver threshold.

Propagation loss and service-threshold evaluation are intentionally
kept separate.

Results are engineering estimates and do not guarantee actual service.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LinkBudgetRequest:
    """Inputs required to evaluate one RF link budget."""

    eirp_dbm: float

    propagation_loss_db: float

    receiver_gain_dbi: float = 0.0

    additional_losses_db: float = 0.0

    receiver_threshold_dbm: float = -100.0

    def __post_init__(self) -> None:
        values = (
            ("eirp_dbm", self.eirp_dbm),
            (
                "propagation_loss_db",
                self.propagation_loss_db,
            ),
            (
                "receiver_gain_dbi",
                self.receiver_gain_dbi,
            ),
            (
                "additional_losses_db",
                self.additional_losses_db,
            ),
            (
                "receiver_threshold_dbm",
                self.receiver_threshold_dbm,
            ),
        )

        for field_name, value in values:
            if not math.isfinite(value):
                raise ValueError(
                    f"{field_name} must be finite; got {value}."
                )

        if self.propagation_loss_db < 0.0:
            raise ValueError(
                "propagation_loss_db must be zero or greater; "
                f"got {self.propagation_loss_db}."
            )

        if self.additional_losses_db < 0.0:
            raise ValueError(
                "additional_losses_db must be zero or greater; "
                f"got {self.additional_losses_db}."
            )


@dataclass(frozen=True)
class LinkBudgetResult:
    """Calculated RF link-budget result."""

    predicted_received_power_dbm: float

    receiver_threshold_dbm: float

    margin_db: float

    meets_threshold: bool


def calculate_received_power_dbm(
    eirp_dbm: float,
    propagation_loss_db: float,
    receiver_gain_dbi: float = 0.0,
    additional_losses_db: float = 0.0,
) -> float:
    """Calculate predicted received power.

    Formula:

        Pr = EIRP
             - propagation loss
             + receiver gain
             - additional losses
    """

    values = (
        ("eirp_dbm", eirp_dbm),
        (
            "propagation_loss_db",
            propagation_loss_db,
        ),
        (
            "receiver_gain_dbi",
            receiver_gain_dbi,
        ),
        (
            "additional_losses_db",
            additional_losses_db,
        ),
    )

    for field_name, value in values:
        if not math.isfinite(value):
            raise ValueError(
                f"{field_name} must be finite; got {value}."
            )

    if propagation_loss_db < 0.0:
        raise ValueError(
            "propagation_loss_db must be zero or greater; "
            f"got {propagation_loss_db}."
        )

    if additional_losses_db < 0.0:
        raise ValueError(
            "additional_losses_db must be zero or greater; "
            f"got {additional_losses_db}."
        )

    return (
        eirp_dbm
        - propagation_loss_db
        + receiver_gain_dbi
        - additional_losses_db
    )


def evaluate_link_budget(
    request: LinkBudgetRequest,
) -> LinkBudgetResult:
    """Evaluate predicted received power against a threshold."""

    received_power_dbm = (
        calculate_received_power_dbm(
            eirp_dbm=request.eirp_dbm,
            propagation_loss_db=(
                request.propagation_loss_db
            ),
            receiver_gain_dbi=(
                request.receiver_gain_dbi
            ),
            additional_losses_db=(
                request.additional_losses_db
            ),
        )
    )

    margin_db = (
        received_power_dbm
        - request.receiver_threshold_dbm
    )

    return LinkBudgetResult(
        predicted_received_power_dbm=(
            received_power_dbm
        ),
        receiver_threshold_dbm=(
            request.receiver_threshold_dbm
        ),
        margin_db=margin_db,
        meets_threshold=(
            margin_db >= 0.0
        ),
    )