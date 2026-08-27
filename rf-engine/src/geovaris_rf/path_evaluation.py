"""GeoVaris RF path evaluation orchestration.

This module combines propagation, optional clutter loss, and link-budget
evaluation while preserving model lineage and engineering assumptions.

Propagation loss and clutter loss remain separate components.

It does not implement propagation or clutter attenuation itself and does
not guarantee service availability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from geovaris_rf.clutter_loss import (
    ClutterLossResult,
)
from geovaris_rf.link_budget import (
    LinkBudgetRequest,
    LinkBudgetResult,
    evaluate_link_budget,
)
from geovaris_rf.propagation import (
    PropagationModel,
    PropagationRequest,
    PropagationResult,
)


@dataclass(frozen=True)
class PathEvaluationRequest:
    """Inputs required to evaluate one RF path."""

    propagation_request: PropagationRequest

    eirp_dbm: float

    clutter_loss: ClutterLossResult | None = None

    receiver_gain_dbi: float = 0.0

    additional_losses_db: float = 0.0

    receiver_threshold_dbm: float = -100.0


@dataclass(frozen=True)
class PathEvaluationResult:
    """Combined propagation, clutter, and threshold-evaluation result."""

    propagation: PropagationResult

    link_budget: LinkBudgetResult

    clutter_loss: ClutterLossResult | None = None

    @property
    def model_name(self) -> str:
        return self.propagation.model_name

    @property
    def model_version(self) -> str:
        return self.propagation.model_version

    @property
    def propagation_loss_db(self) -> float:
        """Backward-compatible underlying propagation-model loss."""

        return (
            self.propagation
            .basic_transmission_loss_db
        )

    @property
    def terrain_loss_db(self) -> float:
        """Underlying terrain/propagation-model transmission loss."""

        return (
            self.propagation
            .basic_transmission_loss_db
        )

    @property
    def clutter_loss_db(
        self,
    ) -> float | None:
        """Additional clutter loss, or None when clutter was not modeled."""

        if self.clutter_loss is None:
            return None

        return (
            self.clutter_loss
            .clutter_loss_db
        )

    @property
    def total_path_loss_db(self) -> float:
        """Combined propagation and modeled clutter loss."""

        total_loss_db = (
            self.terrain_loss_db
        )

        if self.clutter_loss is not None:
            total_loss_db += (
                self.clutter_loss
                .clutter_loss_db
            )

        return total_loss_db

    @property
    def predicted_received_power_dbm(self) -> float:
        return (
            self.link_budget
            .predicted_received_power_dbm
        )

    @property
    def receiver_threshold_dbm(self) -> float:
        return (
            self.link_budget
            .receiver_threshold_dbm
        )

    @property
    def margin_db(self) -> float:
        return self.link_budget.margin_db

    @property
    def meets_threshold(self) -> bool:
        return (
            self.link_budget
            .meets_threshold
        )


def evaluate_path(
    model: PropagationModel,
    request: PathEvaluationRequest,
) -> PathEvaluationResult:
    """Run propagation and evaluate the resulting link budget.

    The propagation model produces the underlying transmission loss.

    When a clutter-loss result is supplied, that loss is added explicitly
    to the propagation loss before the link budget is evaluated.

    Generic additional losses remain separate from both propagation and
    clutter loss.
    """

    propagation_result = model.calculate(
        request.propagation_request
    )

    terrain_loss_db = (
        propagation_result
        .basic_transmission_loss_db
    )

    total_path_loss_db = (
        terrain_loss_db
    )

    if request.clutter_loss is not None:
        total_path_loss_db += (
            request.clutter_loss
            .clutter_loss_db
        )

    if (
        not math.isfinite(
            total_path_loss_db
        )
        or total_path_loss_db < 0.0
    ):
        raise ValueError(
            "Combined propagation and clutter loss "
            "must be finite and zero or greater; "
            f"got {total_path_loss_db}."
        )

    link_budget_result = (
        evaluate_link_budget(
            LinkBudgetRequest(
                eirp_dbm=request.eirp_dbm,
                propagation_loss_db=(
                    total_path_loss_db
                ),
                receiver_gain_dbi=(
                    request.receiver_gain_dbi
                ),
                additional_losses_db=(
                    request.additional_losses_db
                ),
                receiver_threshold_dbm=(
                    request.receiver_threshold_dbm
                ),
            )
        )
    )

    return PathEvaluationResult(
        propagation=propagation_result,
        link_budget=link_budget_result,
        clutter_loss=(
            request.clutter_loss
        ),
    )