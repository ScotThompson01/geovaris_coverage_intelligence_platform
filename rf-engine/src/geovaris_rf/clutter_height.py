"""Governed clutter-height assumptions for GeoVaris Coverage Intelligence.

This module defines versioned clutter-height profiles used by the
Rapid Coverage Estimate methodology.

Annual NLCD provides land-cover classes, not true physical obstruction
heights. GeoVaris therefore maps NLCD source classes into normalized
GeoVaris clutter categories and applies explicit, governed planning
assumptions for effective obstruction height.

The values represented here are planning assumptions used to construct:

    effective_surface_elevation =
        DEM elevation
        + assumed clutter height

Clutter-height assumptions must be:
- explicit
- versioned
- reproducible
- customer-override capable
- stored with scenario/run lineage

They must not be confused with P.2108 statistical clutter-loss values.

RF results are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from geovaris_rf.clutter import (
    GeoVarisClutterClass,
    NLCD_TO_GEOVARIS_CLUTTER,
    NlcdLandCoverClass,
)


CLUTTER_HEIGHT_UNITS = "m"

GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME = (
    "GeoVaris Default Clutter Height Profile"
)

GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION = "2026.1-demo"

GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_SOURCE = (
    "GeoVaris governed representative clutter-height assumptions "
    "derived primarily from ITU-R P.1812/P.452 guidance, with "
    "GeoVaris planning assumptions for categories without direct "
    "ITU equivalents."
)

GEOVARIS_DEFAULT_CLUTTER_HEIGHTS_M = MappingProxyType(
    {
        GeoVarisClutterClass.WATER: 0.0,
        GeoVarisClutterClass.OPEN: 0.0,
        GeoVarisClutterClass.AGRICULTURE: 4.0,
        GeoVarisClutterClass.DEVELOPED_OPEN: 4.0,
        GeoVarisClutterClass.SUBURBAN: 10.0,
        GeoVarisClutterClass.DENSE_SUBURBAN: 12.0,
        GeoVarisClutterClass.URBAN: 15.0,
        GeoVarisClutterClass.FOREST: 15.0,
        GeoVarisClutterClass.WETLAND: 4.0,
    }
)

GOVERNED_NLCD_CLASSES = (
    NlcdLandCoverClass.OPEN_WATER,
    NlcdLandCoverClass.DEVELOPED_OPEN_SPACE,
    NlcdLandCoverClass.DEVELOPED_LOW_INTENSITY,
    NlcdLandCoverClass.DEVELOPED_MEDIUM_INTENSITY,
    NlcdLandCoverClass.DEVELOPED_HIGH_INTENSITY,
    NlcdLandCoverClass.BARREN_LAND,
    NlcdLandCoverClass.DECIDUOUS_FOREST,
    NlcdLandCoverClass.EVERGREEN_FOREST,
    NlcdLandCoverClass.MIXED_FOREST,
    NlcdLandCoverClass.SHRUB_SCRUB,
    NlcdLandCoverClass.GRASSLAND_HERBACEOUS,
    NlcdLandCoverClass.PASTURE_HAY,
    NlcdLandCoverClass.CULTIVATED_CROPS,
    NlcdLandCoverClass.WOODY_WETLANDS,
    NlcdLandCoverClass.EMERGENT_HERBACEOUS_WETLANDS,
)

GOVERNED_CLUTTER_CATEGORIES = (
    GeoVarisClutterClass.WATER,
    GeoVarisClutterClass.OPEN,
    GeoVarisClutterClass.AGRICULTURE,
    GeoVarisClutterClass.DEVELOPED_OPEN,
    GeoVarisClutterClass.SUBURBAN,
    GeoVarisClutterClass.DENSE_SUBURBAN,
    GeoVarisClutterClass.URBAN,
    GeoVarisClutterClass.FOREST,
    GeoVarisClutterClass.WETLAND,
)


@dataclass(frozen=True)
class ClutterHeightClass:
    """One governed NLCD clutter-height assumption."""

    nlcd_class_value: int
    nlcd_class_name: str
    clutter_category: GeoVarisClutterClass
    height_m: float


@dataclass(frozen=True)
class ClutterHeightProfile:
    """Versioned clutter-height profile."""

    name: str
    version: str
    source: str
    units: str
    classes: Mapping[int, ClutterHeightClass]

    def get_height_m(
        self,
        nlcd_class_value: int,
    ) -> float:
        """Return effective clutter height for one NLCD class."""

        try:
            clutter_class = self.classes[int(nlcd_class_value)]
        except KeyError as exc:
            raise KeyError(
                "No clutter-height assumption exists for "
                f"NLCD class {nlcd_class_value}."
            ) from exc

        return clutter_class.height_m

    def get_class(
        self,
        nlcd_class_value: int,
    ) -> ClutterHeightClass:
        """Return full governed class metadata for one NLCD value."""

        try:
            return self.classes[int(nlcd_class_value)]
        except KeyError as exc:
            raise KeyError(
                "No clutter-height assumption exists for "
                f"NLCD class {nlcd_class_value}."
            ) from exc


def _validate_non_empty(
    value: str,
    *,
    name: str,
) -> str:
    """Validate a required string."""

    cleaned = str(value).strip()

    if not cleaned:
        raise ValueError(
            f"{name} must not be empty."
        )

    return cleaned


def _validate_height_m(
    height_m: float,
) -> float:
    """Validate one effective clutter height."""

    numeric_value = float(height_m)

    if not math.isfinite(numeric_value):
        raise ValueError(
            "Clutter height must be finite."
        )

    if numeric_value < 0:
        raise ValueError(
            "Clutter height must be greater than "
            "or equal to zero."
        )

    return numeric_value


def _nlcd_display_name(
    nlcd_class: NlcdLandCoverClass,
) -> str:
    """Create a stable human-readable label from the NLCD enum."""

    return (
        nlcd_class.name
        .replace("_", " ")
        .title()
    )


def _normalize_clutter_category(
    value: GeoVarisClutterClass | str,
) -> GeoVarisClutterClass:
    """Normalize one clutter-category identifier."""

    if isinstance(
        value,
        GeoVarisClutterClass,
    ):
        return value

    try:
        return GeoVarisClutterClass(
            str(value).strip()
        )
    except ValueError as exc:
        raise ValueError(
            "Unsupported GeoVaris clutter category: "
            f"{value!r}."
        ) from exc


def build_clutter_height_class(
    *,
    nlcd_class_value: int,
    nlcd_class_name: str,
    clutter_category: GeoVarisClutterClass | str,
    height_m: float,
) -> ClutterHeightClass:
    """Build and validate one clutter-height class."""

    if isinstance(
        nlcd_class_value,
        bool,
    ):
        raise ValueError(
            "NLCD class value must be an integer."
        )

    class_value = int(nlcd_class_value)

    if class_value < 0:
        raise ValueError(
            "NLCD class value must be greater than "
            "or equal to zero."
        )

    class_name = _validate_non_empty(
        nlcd_class_name,
        name="NLCD class name",
    )

    normalized_category = _normalize_clutter_category(
        clutter_category
    )

    validated_height_m = _validate_height_m(
        height_m
    )

    return ClutterHeightClass(
        nlcd_class_value=class_value,
        nlcd_class_name=class_name,
        clutter_category=normalized_category,
        height_m=validated_height_m,
    )


def build_clutter_height_profile(
    *,
    name: str,
    version: str,
    source: str,
    classes: list[ClutterHeightClass],
) -> ClutterHeightProfile:
    """Build and validate a versioned clutter-height profile."""

    profile_name = _validate_non_empty(
        name,
        name="Profile name",
    )

    profile_version = _validate_non_empty(
        version,
        name="Profile version",
    )

    profile_source = _validate_non_empty(
        source,
        name="Profile source",
    )

    if not classes:
        raise ValueError(
            "Clutter-height profile must contain "
            "at least one class."
        )

    class_mapping: dict[int, ClutterHeightClass] = {}

    for clutter_class in classes:
        class_value = clutter_class.nlcd_class_value

        if class_value in class_mapping:
            raise ValueError(
                "Duplicate NLCD class value in "
                "clutter-height profile: "
                f"{class_value}."
            )

        class_mapping[class_value] = clutter_class

    return ClutterHeightProfile(
        name=profile_name,
        version=profile_version,
        source=profile_source,
        units=CLUTTER_HEIGHT_UNITS,
        classes=class_mapping,
    )


def build_governed_clutter_height_profile(
    *,
    name: str,
    version: str,
    source: str,
    category_heights_m: Mapping[
        GeoVarisClutterClass | str,
        float,
    ],
) -> ClutterHeightProfile:
    """Build the complete governed GeoVaris NLCD height profile.

    Callers provide one explicit effective height for every normalized
    GeoVaris clutter category.

    The category values are then expanded into the complete governed
    set of Annual NLCD source classes.

    No default heights are silently supplied by this function.
    """

    normalized_heights: dict[
        GeoVarisClutterClass,
        float,
    ] = {}

    for category_value, height_m in category_heights_m.items():
        category = _normalize_clutter_category(
            category_value
        )

        if category in normalized_heights:
            raise ValueError(
                "Duplicate clutter-height category: "
                f"{category.value}."
            )

        normalized_heights[category] = _validate_height_m(
            height_m
        )

    required_categories = set(
        GOVERNED_CLUTTER_CATEGORIES
    )

    provided_categories = set(
        normalized_heights.keys()
    )

    missing_categories = (
        required_categories
        - provided_categories
    )

    if missing_categories:
        raise ValueError(
            "Clutter-height profile is missing "
            "required GeoVaris categories: "
            + ", ".join(
                category.value
                for category in sorted(
                    missing_categories,
                    key=lambda item: item.value,
                )
            )
            + "."
        )

    unexpected_categories = (
        provided_categories
        - required_categories
    )

    if unexpected_categories:
        raise ValueError(
            "Clutter-height profile contains "
            "unexpected GeoVaris categories: "
            + ", ".join(
                category.value
                for category in sorted(
                    unexpected_categories,
                    key=lambda item: item.value,
                )
            )
            + "."
        )

    classes: list[ClutterHeightClass] = []

    for nlcd_class in GOVERNED_NLCD_CLASSES:
        category = NLCD_TO_GEOVARIS_CLUTTER[
            nlcd_class
        ]

        classes.append(
            build_clutter_height_class(
                nlcd_class_value=int(
                    nlcd_class
                ),
                nlcd_class_name=_nlcd_display_name(
                    nlcd_class
                ),
                clutter_category=category,
                height_m=normalized_heights[
                    category
                ],
            )
        )

    return build_clutter_height_profile(
        name=name,
        version=version,
        source=source,
        classes=classes,
    )


def build_geovaris_default_clutter_height_profile(
) -> ClutterHeightProfile:
    """Build the governed GeoVaris demo default clutter-height profile.

    These are representative effective obstruction-height assumptions
    for planning use. They are not measurements of actual vegetation
    or building heights at individual locations.

    The profile is explicitly versioned so scenarios and coverage runs
    can preserve the assumptions used for reproducibility.

    This demo profile may be superseded by a later production profile
    following additional validation and calibration.
    """

    return build_governed_clutter_height_profile(
        name=(
            GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME
        ),
        version=(
            GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION
        ),
        source=(
            GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_SOURCE
        ),
        category_heights_m=(
            GEOVARIS_DEFAULT_CLUTTER_HEIGHTS_M
        ),
    )


def apply_clutter_height_overrides(
    *,
    base_profile: ClutterHeightProfile,
    profile_name: str,
    profile_version: str,
    source: str,
    overrides_m: Mapping[int, float],
) -> ClutterHeightProfile:
    """Return a new profile with selected NLCD-class overrides.

    The base profile is not mutated.

    This lower-level interface supports exact NLCD-class overrides.
    Customer-facing configuration will normally operate on normalized
    GeoVaris clutter categories instead.
    """

    updated_classes: list[
        ClutterHeightClass
    ] = []

    for class_value, clutter_class in base_profile.classes.items():
        height_m = (
            overrides_m[class_value]
            if class_value in overrides_m
            else clutter_class.height_m
        )

        updated_classes.append(
            build_clutter_height_class(
                nlcd_class_value=class_value,
                nlcd_class_name=(
                    clutter_class.nlcd_class_name
                ),
                clutter_category=(
                    clutter_class.clutter_category
                ),
                height_m=height_m,
            )
        )

    unknown_classes = (
        set(
            int(value)
            for value in overrides_m.keys()
        )
        - set(
            base_profile.classes.keys()
        )
    )

    if unknown_classes:
        raise ValueError(
            "Clutter-height overrides contain "
            "unknown NLCD class values: "
            + ", ".join(
                str(value)
                for value in sorted(
                    unknown_classes
                )
            )
            + "."
        )

    return build_clutter_height_profile(
        name=profile_name,
        version=profile_version,
        source=source,
        classes=updated_classes,
    )