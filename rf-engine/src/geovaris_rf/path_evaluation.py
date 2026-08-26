"""GeoVaris RF path evaluation orchestration.

This module combines a propagation model result with a link-budget
evaluation while preserving model lineage and engineering assumptions.

It does not implement propagation itself and does not guarantee
service availability.
"""

from __future__ import annotations

from dataclasses import dataclass

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

    receiver_gain_dbi: float = 0.0

    additional_losses_db: float = 0.0

    receiver_threshold_dbm: float = -100.0


@dataclass(frozen=True)
class PathEvaluationResult:
    """Combined propagation and threshold-evaluation result."""

    propagation: PropagationResult

    link_budget: LinkBudgetResult

    @property
    def model_name(self) -> str:
        return self.propagation.model_name

    @property
    def model_version(self) -> str:
        return self.propagation.model_version

    @property
    def propagation_loss_db(self) -> float:
        return (
            self.propagation
            .basic_transmission_loss_db
        )

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
    """Run propagation and evaluate the resulting link budget."""

    propagation_result = model.calculate(
        request.propagation_request
    )

    link_budget_result = (
        evaluate_link_budget(
            LinkBudgetRequest(
                eirp_dbm=request.eirp_dbm,
                propagation_loss_db=(
                    propagation_result
                    .basic_transmission_loss_db
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
    )