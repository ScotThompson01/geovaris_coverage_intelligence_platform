"""Propagation-model contracts for GeoVaris Coverage Intelligence.

This module defines GeoVaris-owned request/result structures and the
interface that propagation engines must implement.

The purpose is to prevent higher-level application code from becoming
directly coupled to a specific RF library such as NTIA ITM.

Important:
- A propagation result is an engineering estimate.
- Path loss is not the same as received power.
- Received power is not the same as guaranteed service.
- LOS and Fresnel analysis remain separate diagnostic calculations.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from geovaris_rf.terrain_profile import TerrainProfile


MIN_SUPPORTED_FREQUENCY_MHZ = 600.0
MAX_SUPPORTED_FREQUENCY_MHZ = 6000.0


@dataclass(frozen=True)
class PropagationRequest:
    """Normalized input to a GeoVaris propagation model.

    The terrain profile is already sampled and projected by the
    terrain-processing subsystem.

    Model-specific parameters should be carried separately in
    model_parameters instead of being silently hard-coded.
    """

    frequency_mhz: float
    transmitter_height_agl_m: float
    receiver_height_agl_m: float
    terrain_profile: TerrainProfile

    model_parameters: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Validate common propagation inputs."""

        if not math.isfinite(
            self.frequency_mhz
        ):
            raise ValueError(
                "frequency_mhz must be finite; "
                f"got {self.frequency_mhz}."
            )

        if (
            self.frequency_mhz
            < MIN_SUPPORTED_FREQUENCY_MHZ
            or self.frequency_mhz
            > MAX_SUPPORTED_FREQUENCY_MHZ
        ):
            raise ValueError(
                "frequency_mhz must be between "
                f"{MIN_SUPPORTED_FREQUENCY_MHZ:g} and "
                f"{MAX_SUPPORTED_FREQUENCY_MHZ:g} MHz; "
                f"got {self.frequency_mhz}."
            )

        if not math.isfinite(
            self.transmitter_height_agl_m
        ):
            raise ValueError(
                "transmitter_height_agl_m must be finite; "
                f"got {self.transmitter_height_agl_m}."
            )

        if self.transmitter_height_agl_m < 0:
            raise ValueError(
                "transmitter_height_agl_m must be zero or greater; "
                f"got {self.transmitter_height_agl_m}."
            )

        if not math.isfinite(
            self.receiver_height_agl_m
        ):
            raise ValueError(
                "receiver_height_agl_m must be finite; "
                f"got {self.receiver_height_agl_m}."
            )

        if self.receiver_height_agl_m < 0:
            raise ValueError(
                "receiver_height_agl_m must be zero or greater; "
                f"got {self.receiver_height_agl_m}."
            )

        if len(
            self.terrain_profile.samples
        ) < 2:
            raise ValueError(
                "terrain_profile must contain at least "
                "two samples for propagation analysis."
            )

        if (
            not math.isfinite(
                self.terrain_profile.total_distance_m
            )
            or self.terrain_profile.total_distance_m <= 0
        ):
            raise ValueError(
                "terrain_profile.total_distance_m must be "
                "finite and greater than zero; "
                f"got "
                f"{self.terrain_profile.total_distance_m}."
            )


@dataclass(frozen=True)
class PropagationResult:
    """Normalized output from a GeoVaris propagation model."""

    model_name: str
    model_version: str

    basic_transmission_loss_db: float

    propagation_mode: str | None = None

    warnings: tuple[str, ...] = ()

    assumptions: dict[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Validate common propagation output."""

        if not self.model_name.strip():
            raise ValueError(
                "model_name cannot be empty."
            )

        if not self.model_version.strip():
            raise ValueError(
                "model_version cannot be empty."
            )

        if not math.isfinite(
            self.basic_transmission_loss_db
        ):
            raise ValueError(
                "basic_transmission_loss_db must be finite; "
                f"got {self.basic_transmission_loss_db}."
            )

        if self.basic_transmission_loss_db < 0:
            raise ValueError(
                "basic_transmission_loss_db cannot be negative; "
                f"got {self.basic_transmission_loss_db}."
            )


class PropagationModel(ABC):
    """Abstract interface implemented by propagation engines."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Human-readable propagation model name."""

        raise NotImplementedError

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Exact implementation/model version."""

        raise NotImplementedError

    @abstractmethod
    def calculate(
        self,
        request: PropagationRequest,
    ) -> PropagationResult:
        """Calculate propagation loss for one path."""

        raise NotImplementedError