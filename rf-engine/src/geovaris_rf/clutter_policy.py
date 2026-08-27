"""GeoVaris clutter-model applicability policy.

This module determines whether the current GeoVaris P.2108 terrestrial
clutter model is applicable to a normalized clutter class.

It does not calculate attenuation.

"Not applicable" is intentionally distinct from "0 dB clutter loss."
Unsupported clutter environments should remain explicit so future models
such as vegetation-specific attenuation can be added without ambiguity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)


class ClutterApplicabilityStatus(
    StrEnum
):
    """Outcome of evaluating clutter-model applicability."""

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    FUTURE_MODEL = "future_model"


@dataclass(frozen=True)
class ClutterApplicability:
    """Applicability decision for one clutter class."""

    clutter_class: GeoVarisClutterClass
    status: ClutterApplicabilityStatus

    model_name: str | None
    reason: str


P2108_MODEL_NAME = (
    "ITU-R P.2108-1 §3.2"
)


def evaluate_p2108_applicability(
    clutter_class: GeoVarisClutterClass,
) -> ClutterApplicability:
    """Evaluate whether P.2108-1 §3.2 applies to a clutter class."""

    if not isinstance(
        clutter_class,
        GeoVarisClutterClass,
    ):
        raise ValueError(
            "clutter_class must be a "
            "GeoVarisClutterClass value."
        )

    if clutter_class in (
        GeoVarisClutterClass.SUBURBAN,
        GeoVarisClutterClass.DENSE_SUBURBAN,
        GeoVarisClutterClass.URBAN,
    ):
        return ClutterApplicability(
            clutter_class=clutter_class,
            status=(
                ClutterApplicabilityStatus.APPLICABLE
            ),
            model_name=P2108_MODEL_NAME,
            reason=(
                "P.2108-1 §3.2 is applicable to "
                "urban/suburban terminal clutter."
            ),
        )

    if clutter_class == (
        GeoVarisClutterClass.FOREST
    ):
        return ClutterApplicability(
            clutter_class=clutter_class,
            status=(
                ClutterApplicabilityStatus.FUTURE_MODEL
            ),
            model_name=None,
            reason=(
                "Forest clutter is not modeled by "
                "the current P.2108-1 §3.2 policy; "
                "a vegetation-specific model is "
                "required."
            ),
        )

    if clutter_class == (
        GeoVarisClutterClass.DEVELOPED_OPEN
    ):
        return ClutterApplicability(
            clutter_class=clutter_class,
            status=(
                ClutterApplicabilityStatus.NOT_APPLICABLE
            ),
            model_name=None,
            reason=(
                "Developed open space is not "
                "treated as urban/suburban terminal "
                "clutter by the current GeoVaris "
                "P.2108 policy."
            ),
        )

    return ClutterApplicability(
        clutter_class=clutter_class,
        status=(
            ClutterApplicabilityStatus.NOT_APPLICABLE
        ),
        model_name=None,
        reason=(
            "The current GeoVaris P.2108 policy "
            "does not apply a terrestrial terminal "
            "clutter correction to this class."
        ),
    )