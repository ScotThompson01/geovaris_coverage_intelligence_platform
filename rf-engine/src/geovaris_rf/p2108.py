"""ITU-R P.2108-1 terrestrial statistical clutter-loss model.

Implements Recommendation ITU-R P.2108-1 Annex 1 Section 3.2:

    Statistical clutter loss model for terrestrial paths

The model is applicable to terrestrial terminals within urban or
suburban clutter over the frequency range 0.5 GHz to 67 GHz.

Clutter loss is an additional statistical correction and remains
separate from the underlying terrain propagation model such as NTIA ITM.

RF results produced using this model are engineering estimates and do
not guarantee service availability.
"""

from __future__ import annotations

import math
from enum import StrEnum
from statistics import NormalDist
from typing import Any

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
)
from geovaris_rf.clutter_loss import (
    ClutterLossModel,
    ClutterLossRequest,
    ClutterLossResult,
)


MIN_FREQUENCY_MHZ = 500.0
MAX_FREQUENCY_MHZ = 67_000.0

ONE_END_MIN_DISTANCE_M = 250.0
BOTH_ENDS_MIN_DISTANCE_M = 1_000.0

MAXIMUM_LOSS_DISTANCE_KM = 2.0

DEVELOPMENT_MEASUREMENT_MAX_HEIGHT_M = 6.0

SIGMA_LONG_DB = 4.0
SIGMA_SHORT_DB = 6.0


SUPPORTED_CLUTTER_CLASSES = frozenset(
    {
        GeoVarisClutterClass.SUBURBAN,
        GeoVarisClutterClass.DENSE_SUBURBAN,
        GeoVarisClutterClass.URBAN,
    }
)


class P2108CorrectionEnd(
    StrEnum
):
    """Terminal end or ends receiving the clutter correction."""

    TRANSMITTER = "transmitter"
    RECEIVER = "receiver"
    BOTH = "both"


class P2108TerrestrialClutterModel(
    ClutterLossModel
):
    """ITU-R P.2108-1 Section 3.2 statistical clutter model."""

    @property
    def model_name(
        self,
    ) -> str:
        return (
            "ITU-R P.2108 Terrestrial "
            "Statistical Clutter"
        )

    @property
    def model_version(
        self,
    ) -> str:
        return "P.2108-1 (09/2021) §3.2"

    def calculate(
        self,
        request: ClutterLossRequest,
    ) -> ClutterLossResult:
        """Calculate statistical terrestrial clutter loss."""

        self._validate_frequency(
            request.frequency_mhz
        )

        self._validate_clutter_class(
            request.clutter_class
        )

        percentage_locations = (
            self._percentage_locations(
                request.model_parameters
            )
        )

        correction_end = (
            self._correction_end(
                request.model_parameters
            )
        )

        self._validate_distance(
            path_distance_m=(
                request.path_distance_m
            ),
            correction_end=(
                correction_end
            ),
        )

        frequency_ghz = (
            request.frequency_mhz
            / 1000.0
        )

        distance_km = (
            request.path_distance_m
            / 1000.0
        )

        raw_loss_db = (
            _terrestrial_clutter_loss_db(
                frequency_ghz=frequency_ghz,
                distance_km=distance_km,
                percentage_locations=(
                    percentage_locations
                ),
            )
        )

        maximum_loss_db = (
            _terrestrial_clutter_loss_db(
                frequency_ghz=frequency_ghz,
                distance_km=(
                    MAXIMUM_LOSS_DISTANCE_KM
                ),
                percentage_locations=(
                    percentage_locations
                ),
            )
        )

        clutter_loss_db = min(
            raw_loss_db,
            maximum_loss_db,
        )

        warnings = (
            self._terminal_height_warnings(
                request=request,
                correction_end=(
                    correction_end
                ),
            )
        )

        return ClutterLossResult(
            model_name=self.model_name,
            model_version=self.model_version,
            clutter_loss_db=(
                clutter_loss_db
            ),
            warnings=warnings,
            assumptions={
                "recommendation":
                    "ITU-R P.2108-1",
                "section":
                    "Annex 1 §3.2",
                "frequency_ghz":
                    frequency_ghz,
                "path_distance_km":
                    distance_km,
                "percentage_locations":
                    percentage_locations,
                "correction_end":
                    correction_end.value,
                "clutter_class":
                    request.clutter_class.value,
                "maximum_loss_distance_km":
                    MAXIMUM_LOSS_DISTANCE_KM,
                "raw_clutter_loss_db":
                    raw_loss_db,
                "maximum_clutter_loss_db":
                    maximum_loss_db,
                "capped_to_2km":
                    raw_loss_db
                    > maximum_loss_db,
                "terminal_height_note": (
                    "P.2108-1 §3.2 is intended "
                    "for terminals well below "
                    "representative clutter height; "
                    "development measurements used "
                    "terminal heights up to 6 m."
                ),
                "engineering_estimate":
                    True,
            },
        )

    @staticmethod
    def _validate_frequency(
        frequency_mhz: float,
    ) -> None:
        frequency = float(
            frequency_mhz
        )

        if (
            frequency
            < MIN_FREQUENCY_MHZ
            or frequency
            > MAX_FREQUENCY_MHZ
        ):
            raise ValueError(
                "ITU-R P.2108-1 §3.2 frequency "
                "must be between "
                f"{MIN_FREQUENCY_MHZ:g} and "
                f"{MAX_FREQUENCY_MHZ:g} MHz; "
                f"got {frequency:g} MHz."
            )

    @staticmethod
    def _validate_clutter_class(
        clutter_class: GeoVarisClutterClass,
    ) -> None:
        if (
            clutter_class
            not in SUPPORTED_CLUTTER_CLASSES
        ):
            supported = ", ".join(
                sorted(
                    clutter.value
                    for clutter
                    in SUPPORTED_CLUTTER_CLASSES
                )
            )

            raise ValueError(
                "ITU-R P.2108-1 §3.2 is limited "
                "to urban/suburban clutter. "
                f"Supported GeoVaris classes: "
                f"{supported}; got "
                f"{clutter_class.value}."
            )

    @staticmethod
    def _percentage_locations(
        model_parameters: dict[str, Any],
    ) -> float:
        if (
            "percentage_locations"
            not in model_parameters
        ):
            raise ValueError(
                "percentage_locations must be "
                "explicitly configured for "
                "ITU-R P.2108-1 §3.2."
            )

        value = model_parameters[
            "percentage_locations"
        ]

        if isinstance(
            value,
            bool,
        ):
            raise ValueError(
                "percentage_locations must be "
                "numeric."
            )

        try:
            percentage = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "percentage_locations must be "
                "numeric."
            ) from exc

        if (
            not math.isfinite(
                percentage
            )
            or percentage <= 0.0
            or percentage >= 100.0
        ):
            raise ValueError(
                "percentage_locations must satisfy "
                "0 < p < 100."
            )

        return percentage

    @staticmethod
    def _correction_end(
        model_parameters: dict[str, Any],
    ) -> P2108CorrectionEnd:
        if (
            "correction_end"
            not in model_parameters
        ):
            raise ValueError(
                "correction_end must be explicitly "
                "configured for ITU-R P.2108-1 §3.2."
            )

        value = model_parameters[
            "correction_end"
        ]

        try:
            return P2108CorrectionEnd(
                value
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "correction_end must be one of: "
                "transmitter, receiver, both."
            ) from exc

    @staticmethod
    def _validate_distance(
        *,
        path_distance_m: float,
        correction_end: P2108CorrectionEnd,
    ) -> None:
        distance_m = float(
            path_distance_m
        )

        if (
            correction_end
            == P2108CorrectionEnd.BOTH
        ):
            minimum_distance_m = (
                BOTH_ENDS_MIN_DISTANCE_M
            )
        else:
            minimum_distance_m = (
                ONE_END_MIN_DISTANCE_M
            )

        if (
            distance_m
            < minimum_distance_m
        ):
            raise ValueError(
                "ITU-R P.2108-1 §3.2 path "
                "distance is below the minimum "
                f"for correction_end="
                f"{correction_end.value}: "
                f"{minimum_distance_m:g} m "
                f"required; got {distance_m:g} m."
            )

    @staticmethod
    def _terminal_height_warnings(
        *,
        request: ClutterLossRequest,
        correction_end: P2108CorrectionEnd,
    ) -> tuple[str, ...]:
        warnings: list[str] = []

        if correction_end in (
            P2108CorrectionEnd.TRANSMITTER,
            P2108CorrectionEnd.BOTH,
        ):
            if (
                request.transmitter_height_agl_m
                > DEVELOPMENT_MEASUREMENT_MAX_HEIGHT_M
            ):
                warnings.append(
                    "Transmitter terminal height "
                    "exceeds 6 m; P.2108-1 §3.2 "
                    "development measurements used "
                    "terminal heights up to 6 m."
                )

        if correction_end in (
            P2108CorrectionEnd.RECEIVER,
            P2108CorrectionEnd.BOTH,
        ):
            if (
                request.receiver_height_agl_m
                > DEVELOPMENT_MEASUREMENT_MAX_HEIGHT_M
            ):
                warnings.append(
                    "Receiver terminal height "
                    "exceeds 6 m; P.2108-1 §3.2 "
                    "development measurements used "
                    "terminal heights up to 6 m."
                )

        return tuple(
            warnings
        )


def _terrestrial_clutter_loss_db(
    *,
    frequency_ghz: float,
    distance_km: float,
    percentage_locations: float,
) -> float:
    """Evaluate P.2108-1 Annex 1 §3.2 equations."""

    log_frequency = math.log10(
        frequency_ghz
    )

    long_component_db = (
        -2.0
        * math.log10(
            (
                10.0
                ** (
                    -5.0
                    * log_frequency
                    - 12.5
                )
            )
            + (
                10.0
                ** -16.5
            )
        )
    )

    short_component_db = (
        32.98
        + (
            23.9
            * math.log10(
                distance_km
            )
        )
        + (
            3.0
            * log_frequency
        )
    )

    long_weight = (
        10.0
        ** (
            -0.2
            * long_component_db
        )
    )

    short_weight = (
        10.0
        ** (
            -0.2
            * short_component_db
        )
    )

    combined_weight = (
        long_weight
        + short_weight
    )

    sigma_cb_db = math.sqrt(
        (
            (
                SIGMA_LONG_DB
                ** 2
            )
            * long_weight
            + (
                SIGMA_SHORT_DB
                ** 2
            )
            * short_weight
        )
        / combined_weight
    )

    location_fraction = (
        percentage_locations
        / 100.0
    )

    inverse_complementary_normal = (
        NormalDist().inv_cdf(
            1.0
            - location_fraction
        )
    )

    return (
        -5.0
        * math.log10(
            combined_weight
        )
        - (
            sigma_cb_db
            * inverse_complementary_normal
        )
    )