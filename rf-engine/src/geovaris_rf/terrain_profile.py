"""Terrain profile sampling for GeoVaris Coverage Intelligence.

This module converts a site-to-target path into regularly spaced
terrain elevation samples from a local projected DEM.

Terrain profiles are an input to propagation calculations. They are
not, by themselves, an RF propagation model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer

from geovaris_rf.dem import validate_coordinate


@dataclass(frozen=True)
class TerrainProfileSample:
    """One terrain sample along an RF path."""

    distance_m: float
    latitude: float
    longitude: float
    x_m: float
    y_m: float
    elevation_m: float


@dataclass(frozen=True)
class TerrainProfile:
    """Terrain elevation profile between two geographic points."""

    raster_path: str
    raster_crs: str
    total_distance_m: float
    requested_spacing_m: float
    actual_spacing_m: float
    samples: tuple[TerrainProfileSample, ...]


def _validate_sample_spacing(
    sample_spacing_m: float,
) -> None:
    """Validate terrain-profile sample spacing."""

    if sample_spacing_m <= 0:
        raise ValueError(
            "sample_spacing_m must be greater than zero; "
            f"got {sample_spacing_m}."
        )


def _project_path_endpoints(
    raster_crs: str,
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
) -> tuple[float, float, float, float]:
    """Project WGS84 path endpoints into the DEM CRS."""

    transformer = Transformer.from_crs(
        "EPSG:4326",
        raster_crs,
        always_xy=True,
    )

    start_x_m, start_y_m = transformer.transform(
        start_longitude,
        start_latitude,
    )

    end_x_m, end_y_m = transformer.transform(
        end_longitude,
        end_latitude,
    )

    return (
        float(start_x_m),
        float(start_y_m),
        float(end_x_m),
        float(end_y_m),
    )


def _calculate_sample_count(
    total_distance_m: float,
    sample_spacing_m: float,
) -> int:
    """Return number of samples including both path endpoints."""

    if total_distance_m == 0:
        return 1

    segment_count = math.ceil(
        total_distance_m
        / sample_spacing_m
    )

    return segment_count + 1


def sample_terrain_profile(
    raster_path: str,
    start_latitude: float,
    start_longitude: float,
    end_latitude: float,
    end_longitude: float,
    sample_spacing_m: float = 30.0,
) -> TerrainProfile:
    """Sample terrain elevations along a site-to-target path.

    The geographic endpoints are transformed from EPSG:4326 into the
    DEM's projected CRS. The path is then sampled at approximately the
    requested spacing.

    Both endpoints are always included.

    For local UTM terrain grids this provides a practical RF terrain
    profile suitable for later propagation-model integration.
    """

    validate_coordinate(
        start_latitude,
        start_longitude,
    )

    validate_coordinate(
        end_latitude,
        end_longitude,
    )

    _validate_sample_spacing(
        sample_spacing_m
    )

    path = Path(
        raster_path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"Terrain raster does not exist: {raster_path}"
        )

    with rasterio.open(
        path
    ) as dataset:
        if dataset.crs is None:
            raise RuntimeError(
                f"Terrain raster has no CRS: {raster_path}"
            )

        raster_crs = str(
            dataset.crs
        )

        (
            start_x_m,
            start_y_m,
            end_x_m,
            end_y_m,
        ) = _project_path_endpoints(
            raster_crs=raster_crs,
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            end_latitude=end_latitude,
            end_longitude=end_longitude,
        )

        delta_x_m = (
            end_x_m
            - start_x_m
        )

        delta_y_m = (
            end_y_m
            - start_y_m
        )

        total_distance_m = math.hypot(
            delta_x_m,
            delta_y_m,
        )

        sample_count = _calculate_sample_count(
            total_distance_m=total_distance_m,
            sample_spacing_m=sample_spacing_m,
        )

        if sample_count == 1:
            fractions = np.array(
                [0.0],
                dtype=np.float64,
            )

            actual_spacing_m = 0.0

        else:
            fractions = np.linspace(
                0.0,
                1.0,
                sample_count,
                dtype=np.float64,
            )

            actual_spacing_m = (
                total_distance_m
                / (sample_count - 1)
            )

        x_values = (
            start_x_m
            + fractions * delta_x_m
        )

        y_values = (
            start_y_m
            + fractions * delta_y_m
        )

        inverse_transformer = Transformer.from_crs(
            raster_crs,
            "EPSG:4326",
            always_xy=True,
        )

        longitudes, latitudes = (
            inverse_transformer.transform(
                x_values,
                y_values,
            )
        )

        coordinates = list(
            zip(
                x_values.tolist(),
                y_values.tolist(),
            )
        )

        raw_samples = list(
            dataset.sample(
                coordinates,
                indexes=1,
                masked=True,
            )
        )

        profile_samples: list[
            TerrainProfileSample
        ] = []

        for index, raw_sample in enumerate(
            raw_samples
        ):
            value = raw_sample[0]

            if np.ma.is_masked(value):
                raise RuntimeError(
                    "Terrain profile encountered a NoData cell at "
                    f"sample {index}, "
                    f"distance approximately "
                    f"{fractions[index] * total_distance_m:.2f} m."
                )

            elevation_m = float(
                value
            )

            if (
                dataset.nodata is not None
                and math.isclose(
                    elevation_m,
                    float(dataset.nodata),
                    rel_tol=0.0,
                    abs_tol=1e-6,
                )
            ):
                raise RuntimeError(
                    "Terrain profile encountered the raster NoData "
                    f"value at sample {index}."
                )

            distance_m = (
                float(fractions[index])
                * total_distance_m
            )

            profile_samples.append(
                TerrainProfileSample(
                    distance_m=distance_m,
                    latitude=float(
                        latitudes[index]
                    ),
                    longitude=float(
                        longitudes[index]
                    ),
                    x_m=float(
                        x_values[index]
                    ),
                    y_m=float(
                        y_values[index]
                    ),
                    elevation_m=elevation_m,
                )
            )

    return TerrainProfile(
        raster_path=str(path),
        raster_crs=raster_crs,
        total_distance_m=total_distance_m,
        requested_spacing_m=sample_spacing_m,
        actual_spacing_m=actual_spacing_m,
        samples=tuple(
            profile_samples
        ),
    )