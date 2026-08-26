"""GeoVaris coverage-grid geometry planning.

This module creates deterministic projected receiver-cell centers for
an RF coverage calculation.

It does not perform propagation modeling.

Responsibilities:
- Select an appropriate local projected CRS.
- Build a square grid around the transmitter.
- Mark cells whose centers fall inside the requested calculation radius.
- Preserve grid dimensions, bounds, resolution, and CRS.

RF propagation and service-threshold calculations occur in separate
modules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pyproj import Transformer

from geovaris_rf.dem_raster import (
    calculate_utm_epsg,
)


@dataclass(frozen=True)
class CoverageGridPoint:
    """One receiver-cell center in the coverage grid."""

    row: int
    column: int

    x_m: float
    y_m: float

    latitude: float
    longitude: float

    distance_from_site_m: float

    inside_radius: bool


@dataclass(frozen=True)
class CoverageGridPlan:
    """Complete coverage-grid geometry plan."""

    site_latitude: float
    site_longitude: float

    site_x_m: float
    site_y_m: float

    radius_m: float
    resolution_m: float

    crs_epsg: int

    width: int
    height: int

    west_m: float
    south_m: float
    east_m: float
    north_m: float

    points: tuple[CoverageGridPoint, ...]

    @property
    def total_cell_count(self) -> int:
        return self.width * self.height

    @property
    def inside_radius_count(self) -> int:
        return sum(
            1
            for point in self.points
            if point.inside_radius
        )


def _validate_coordinate(
    latitude: float,
    longitude: float,
) -> None:
    if (
        not math.isfinite(latitude)
        or latitude < -90.0
        or latitude > 90.0
    ):
        raise ValueError(
            "latitude must be finite and between "
            f"-90 and 90 degrees; got {latitude}."
        )

    if (
        not math.isfinite(longitude)
        or longitude < -180.0
        or longitude > 180.0
    ):
        raise ValueError(
            "longitude must be finite and between "
            f"-180 and 180 degrees; got {longitude}."
        )


def _validate_positive_finite(
    value: float,
    field_name: str,
) -> None:
    if (
        not math.isfinite(value)
        or value <= 0.0
    ):
        raise ValueError(
            f"{field_name} must be finite and greater "
            f"than zero; got {value}."
        )


def plan_coverage_grid(
    site_latitude: float,
    site_longitude: float,
    radius_m: float,
    resolution_m: float,
) -> CoverageGridPlan:
    """Create a projected square coverage grid.

    The grid is centered on the projected transmitter location.

    The square extent is expanded when necessary so that:

        width * resolution == full grid width
        height * resolution == full grid height

    Cell centers are then classified using their projected Euclidean
    distance from the site.

    For the small/local extents used by GeoVaris coverage calculations,
    a local UTM CRS provides meter-based geometry suitable for grid
    planning.
    """

    _validate_coordinate(
        site_latitude,
        site_longitude,
    )

    _validate_positive_finite(
        radius_m,
        "radius_m",
    )

    _validate_positive_finite(
        resolution_m,
        "resolution_m",
    )

    crs_epsg = calculate_utm_epsg(
        site_latitude,
        site_longitude,
    )

    forward_transformer = (
        Transformer.from_crs(
            "EPSG:4326",
            f"EPSG:{crs_epsg}",
            always_xy=True,
        )
    )

    inverse_transformer = (
        Transformer.from_crs(
            f"EPSG:{crs_epsg}",
            "EPSG:4326",
            always_xy=True,
        )
    )

    site_x_m, site_y_m = (
        forward_transformer.transform(
            site_longitude,
            site_latitude,
        )
    )

    requested_width_m = (
        radius_m * 2.0
    )

    cell_count = int(
        math.ceil(
            requested_width_m
            / resolution_m
        )
    )

    # Keep a symmetric square around the transmitter.
    #
    # An odd number of cells guarantees there is one cell center
    # exactly on the projected transmitter coordinate.
    if cell_count % 2 == 0:
        cell_count += 1

    width = cell_count
    height = cell_count

    full_width_m = (
        width * resolution_m
    )

    half_width_m = (
        full_width_m / 2.0
    )

    west_m = (
        site_x_m
        - half_width_m
    )

    east_m = (
        site_x_m
        + half_width_m
    )

    south_m = (
        site_y_m
        - half_width_m
    )

    north_m = (
        site_y_m
        + half_width_m
    )

    points: list[CoverageGridPoint] = []

    for row in range(height):
        # Raster/grid rows are ordered north to south.
        y_m = (
            north_m
            - (
                row + 0.5
            )
            * resolution_m
        )

        for column in range(width):
            x_m = (
                west_m
                + (
                    column + 0.5
                )
                * resolution_m
            )

            dx_m = (
                x_m
                - site_x_m
            )

            dy_m = (
                y_m
                - site_y_m
            )

            distance_m = math.hypot(
                dx_m,
                dy_m,
            )

            inside_radius = (
                distance_m
                <= radius_m
            )

            longitude, latitude = (
                inverse_transformer.transform(
                    x_m,
                    y_m,
                )
            )

            points.append(
                CoverageGridPoint(
                    row=row,
                    column=column,
                    x_m=float(x_m),
                    y_m=float(y_m),
                    latitude=float(latitude),
                    longitude=float(longitude),
                    distance_from_site_m=float(
                        distance_m
                    ),
                    inside_radius=inside_radius,
                )
            )

    return CoverageGridPlan(
        site_latitude=float(
            site_latitude
        ),
        site_longitude=float(
            site_longitude
        ),
        site_x_m=float(
            site_x_m
        ),
        site_y_m=float(
            site_y_m
        ),
        radius_m=float(
            radius_m
        ),
        resolution_m=float(
            resolution_m
        ),
        crs_epsg=crs_epsg,
        width=width,
        height=height,
        west_m=float(
            west_m
        ),
        south_m=float(
            south_m
        ),
        east_m=float(
            east_m
        ),
        north_m=float(
            north_m
        ),
        points=tuple(
            points
        ),
    )