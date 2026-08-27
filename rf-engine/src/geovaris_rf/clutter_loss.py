"""GeoVaris clutter-loss model contracts.

This module defines the typed interface for clutter-loss calculations.

It intentionally does not implement a specific clutter-loss equation yet.
The calculation model will be added separately after the engineering method
is selected and validated.

Clutter loss is an additional propagation correction and must remain
separate from bare-earth terrain propagation such as NTIA ITM.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)


@dataclass(frozen=True)
class ClutterLossRequest:
    """Inputs required for a clutter-loss calculation."""

    frequency_mhz: float
    clutter_class: GeoVarisClutterClass

    path_distance_m: float

    transmitter_height_agl_m: float
    receiver_height_agl_m: float

    model_parameters: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        _validate_positive_finite(
            self.frequency_mhz,
            "frequency_mhz",
        )

        _validate_nonnegative_finite(
            self.path_distance_m,
            "path_distance_m",
        )

        _validate_nonnegative_finite(
            self.transmitter_height_agl_m,
            "transmitter_height_agl_m",
        )

        _validate_nonnegative_finite(
            self.receiver_height_agl_m,
            "receiver_height_agl_m",
        )

        if not isinstance(
            self.clutter_class,
            GeoVarisClutterClass,
        ):
            raise ValueError(
                "clutter_class must be a "
                "GeoVarisClutterClass value."
            )

        if not isinstance(
            self.model_parameters,
            dict,
        ):
            raise ValueError(
                "model_parameters must be a dictionary."
            )


@dataclass(frozen=True)
class ClutterLossResult:
    """Result returned by a clutter-loss model."""

    model_name: str
    model_version: str

    clutter_loss_db: float

    warnings: tuple[str, ...] = ()
    assumptions: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(
        self,
    ) -> None:
        if not self.model_name.strip():
            raise ValueError(
                "model_name must not be empty."
            )

        if not self.model_version.strip():
            raise ValueError(
                "model_version must not be empty."
            )

        _validate_finite(
            self.clutter_loss_db,
            "clutter_loss_db",
        )

        if not isinstance(
            self.warnings,
            tuple,
        ):
            raise ValueError(
                "warnings must be a tuple."
            )

        if not isinstance(
            self.assumptions,
            dict,
        ):
            raise ValueError(
                "assumptions must be a dictionary."
            )


class ClutterLossModel(
    ABC
):
    """Abstract clutter-loss model interface."""

    @property
    @abstractmethod
    def model_name(
        self,
    ) -> str:
        """Human-readable model name."""

    @property
    @abstractmethod
    def model_version(
        self,
    ) -> str:
        """Model version identifier."""

    @abstractmethod
    def calculate(
        self,
        request: ClutterLossRequest,
    ) -> ClutterLossResult:
        """Calculate additional clutter loss in dB."""

def _validate_finite(
    value: float,
    field_name: str,
) -> None:
    """Validate a finite numeric value."""

    numeric_value = float(
        value
    )

    if not math.isfinite(
        numeric_value
    ):
        raise ValueError(
            f"{field_name} must be finite."
        )    

def _validate_positive_finite(
    value: float,
    field_name: str,
) -> None:
    """Validate a finite value greater than zero."""

    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value <= 0.0
    ):
        raise ValueError(
            f"{field_name} must be a finite value "
            "greater than zero."
        )


def _validate_nonnegative_finite(
    value: float,
    field_name: str,
) -> None:
    """Validate a finite value greater than or equal to zero."""

    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value < 0.0
    ):
        raise ValueError(
            f"{field_name} must be a finite value "
            "greater than or equal to zero."
        )