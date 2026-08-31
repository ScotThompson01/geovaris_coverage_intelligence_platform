"""GeoVaris NTIA ITM development coverage worker.

Processes one pending ``ntia_itm`` coverage run using:

- immutable RF inputs stored on coverage_runs
- immutable ITM assumptions stored on coverage_runs
- optional immutable clutter dataset/model assumptions
- an explicitly configured local working DEM raster
- an explicitly configured local working clutter raster when required
- the validated NTIA ITM 1.4 native library
- GeoVaris coverage-grid, GeoTIFF, and GeoJSON pipelines

For development/testing, GEOVARIS_COVERAGE_RUN_ID may be set to
explicitly select one pending NTIA ITM coverage run. When it is not set,
the oldest pending NTIA ITM run is processed.

This is an MVP development worker. It is not yet the final production
job-queue or object-storage implementation.

RF results are engineering estimates and do not guarantee service.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any

import psycopg
import rasterio
from psycopg.rows import dict_row

from geovaris_rf.artifacts import (
    build_coverage_artifact_paths,
)
from geovaris_rf.coverage_calculation import (
    calculate_coverage_subset,
)
from geovaris_rf.coverage_geojson import (
    coverage_raster_to_geojson,
)
from geovaris_rf.coverage_grid import (
    plan_coverage_grid,
)
from geovaris_rf.coverage_raster import (
    write_coverage_geotiff,
)
from geovaris_rf.itm import (
    ItmClimate,
    ItmConfiguration,
    ItmPolarization,
    ItmVariabilityMode,
)
from geovaris_rf.itm_model import (
    ItmModel,
    default_local_itm_dll_path,
)
from geovaris_rf.storage import (
    LocalCoverageStorage,
)


PROPAGATION_MODEL = "ntia_itm"
MODEL_VERSION = "1.4"

P2108_CLUTTER_MODEL = (
    "ITU-R P.2108 Terrestrial Statistical Clutter"
)

P2108_CLUTTER_MODEL_VERSION = (
    "P.2108-1 (09/2021) §3.2"
)

P2108_CORRECTION_END = "receiver"

DEM_ENVIRONMENT_VARIABLE = (
    "GEOVARIS_ITM_DEM_RASTER_PATH"
)

CLUTTER_ENVIRONMENT_VARIABLE = (
    "GEOVARIS_CLUTTER_RASTER_PATH"
)

OUTPUT_ROOT_ENVIRONMENT_VARIABLE = (
    "GEOVARIS_COVERAGE_OUTPUT_DIR"
)

RUN_ID_ENVIRONMENT_VARIABLE = (
    "GEOVARIS_COVERAGE_RUN_ID"
)

DEFAULT_OUTPUT_ROOT = Path(
    "rf-engine/data/coverage"
)


def get_database_url() -> str:
    """Read the PostgreSQL connection string."""

    database_url = os.getenv(
        "GEOVARIS_DATABASE_URL"
    )

    if not database_url:
        raise RuntimeError(
            "GEOVARIS_DATABASE_URL environment variable "
            "is not configured."
        )

    return database_url


def get_requested_run_id() -> str | None:
    """Return an optional explicitly requested coverage run ID."""

    value = os.getenv(
        RUN_ID_ENVIRONMENT_VARIABLE
    )

    if value is None:
        return None

    value = value.strip()

    return value or None


def _resolve_required_file(
    *,
    environment_variable: str,
    description: str,
) -> Path:
    """Resolve an explicitly configured local working file."""

    configured_path = os.getenv(
        environment_variable
    )

    if not configured_path:
        raise RuntimeError(
            f"{environment_variable} must be configured "
            f"for {description}."
        )

    path = Path(
        configured_path
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"Configured {description} does not exist: "
            f"{path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Configured {description} is not a file: "
            f"{path}"
        )

    return path


def get_dem_raster_path() -> Path:
    """Resolve the explicitly configured working DEM raster."""

    return _resolve_required_file(
        environment_variable=(
            DEM_ENVIRONMENT_VARIABLE
        ),
        description=(
            "ITM DEM raster"
        ),
    )


def get_clutter_raster_path() -> Path:
    """Resolve the explicitly configured working clutter raster."""

    return _resolve_required_file(
        environment_variable=(
            CLUTTER_ENVIRONMENT_VARIABLE
        ),
        description=(
            "NLCD clutter raster"
        ),
    )


def get_output_root() -> Path:
    """Resolve the local development output directory."""

    configured_path = os.getenv(
        OUTPUT_ROOT_ENVIRONMENT_VARIABLE
    )

    if configured_path:
        output_root = Path(
            configured_path
        )
    else:
        output_root = (
            DEFAULT_OUTPUT_ROOT
        )

    output_root = (
        output_root
        .expanduser()
        .resolve()
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    return output_root


def _watts_to_dbm(
    watts: float,
) -> float:
    """Convert watts to dBm."""

    if (
        not math.isfinite(
            watts
        )
        or watts <= 0
    ):
        raise ValueError(
            "EIRP watts must be a finite value "
            "greater than zero."
        )

    return (
        10.0
        * math.log10(
            watts * 1000.0
        )
    )


def _terrain_sample_spacing_m(
    dem_raster_path: Path,
) -> float:
    """Derive terrain sampling spacing from the working raster.

    The working DEM must use a projected meter-based CRS with square
    pixels. This prevents silently mixing geographic degrees with meters.
    """

    with rasterio.open(
        dem_raster_path
    ) as dataset:
        if dataset.crs is None:
            raise ValueError(
                "Working DEM raster does not define a CRS."
            )

        if not dataset.crs.is_projected:
            raise ValueError(
                "Working DEM raster must use a projected CRS "
                "for meter-based terrain sampling."
            )

        x_resolution_m = abs(
            float(
                dataset.transform.a
            )
        )

        y_resolution_m = abs(
            float(
                dataset.transform.e
            )
        )

    if (
        not math.isfinite(
            x_resolution_m
        )
        or not math.isfinite(
            y_resolution_m
        )
        or x_resolution_m <= 0
        or y_resolution_m <= 0
    ):
        raise ValueError(
            "Working DEM raster has an invalid pixel resolution."
        )

    if not math.isclose(
        x_resolution_m,
        y_resolution_m,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ValueError(
            "Working DEM raster must use square pixels; "
            f"got {x_resolution_m} m x "
            f"{y_resolution_m} m."
        )

    return x_resolution_m


def claim_pending_itm_run(
    connection: psycopg.Connection,
) -> dict[str, Any] | None:
    """Claim one pending NTIA ITM coverage run.

    When GEOVARIS_COVERAGE_RUN_ID is configured, only that pending
    NTIA ITM run is eligible. Otherwise the oldest pending NTIA ITM
    run is claimed.
    """

    requested_run_id = (
        get_requested_run_id()
    )

    with connection.transaction():
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            if requested_run_id is None:
                cursor.execute(
                    """
                    SELECT
                        id,
                        customer_id,
                        scenario_id,

                        site_latitude,
                        site_longitude,
                        site_ground_elevation_m,

                        frequency_mhz,
                        eirp_watts,

                        antenna_height_m,
                        antenna_gain_dbi,

                        receiver_height_m,
                        receiver_threshold_dbm,

                        calculation_radius_m,
                        resolution_m,

                        propagation_model,
                        propagation_model_version,

                        itm_climate,
                        itm_polarization,
                        itm_variability_mode,
                        itm_surface_refractivity,
                        itm_dielectric_constant,
                        itm_conductivity_s_per_m,
                        itm_confidence,
                        itm_reliability,

                        clutter_source,
                        clutter_version,
                        clutter_model,
                        clutter_model_version,
                        clutter_percentage_locations,
                        clutter_correction_end,

                        dem_source,
                        dem_version,
                        dem_horizontal_crs,
                        dem_vertical_datum,
                        dem_units,
                        dem_resolution_m

                    FROM coverage_runs

                    WHERE status = 'pending'
                      AND propagation_model = %s

                    ORDER BY created_at

                    FOR UPDATE SKIP LOCKED

                    LIMIT 1;
                    """,
                    (
                        PROPAGATION_MODEL,
                    ),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        id,
                        customer_id,
                        scenario_id,

                        site_latitude,
                        site_longitude,
                        site_ground_elevation_m,

                        frequency_mhz,
                        eirp_watts,

                        antenna_height_m,
                        antenna_gain_dbi,

                        receiver_height_m,
                        receiver_threshold_dbm,

                        calculation_radius_m,
                        resolution_m,

                        propagation_model,
                        propagation_model_version,

                        itm_climate,
                        itm_polarization,
                        itm_variability_mode,
                        itm_surface_refractivity,
                        itm_dielectric_constant,
                        itm_conductivity_s_per_m,
                        itm_confidence,
                        itm_reliability,

                        clutter_source,
                        clutter_version,
                        clutter_model,
                        clutter_model_version,
                        clutter_percentage_locations,
                        clutter_correction_end,

                        dem_source,
                        dem_version,
                        dem_horizontal_crs,
                        dem_vertical_datum,
                        dem_units,
                        dem_resolution_m

                    FROM coverage_runs

                    WHERE id = %s
                      AND status = 'pending'
                      AND propagation_model = %s

                    FOR UPDATE SKIP LOCKED

                    LIMIT 1;
                    """,
                    (
                        requested_run_id,
                        PROPAGATION_MODEL,
                    ),
                )

            coverage_run = (
                cursor.fetchone()
            )

            if coverage_run is None:
                return None

            cursor.execute(
                """
                UPDATE coverage_runs
                SET
                    status = 'processing',
                    started_at = NOW(),
                    completed_at = NULL,
                    error_message = NULL
                WHERE id = %s;
                """,
                (
                    coverage_run[
                        "id"
                    ],
                ),
            )

            return coverage_run


def _validate_run(
    coverage_run: dict[str, Any],
) -> None:
    """Validate required NTIA ITM and optional clutter fields."""

    if (
        coverage_run[
            "propagation_model"
        ]
        != PROPAGATION_MODEL
    ):
        raise ValueError(
            "Coverage run is not an ntia_itm run."
        )

    if (
        coverage_run[
            "propagation_model_version"
        ]
        != MODEL_VERSION
    ):
        raise ValueError(
            "Unsupported NTIA ITM model version: "
            f"{coverage_run['propagation_model_version']!r}."
        )

    required_fields = (
        "site_latitude",
        "site_longitude",
        "frequency_mhz",
        "eirp_watts",
        "antenna_height_m",
        "receiver_height_m",
        "receiver_threshold_dbm",
        "calculation_radius_m",
        "resolution_m",
        "itm_climate",
        "itm_polarization",
        "itm_variability_mode",
        "itm_surface_refractivity",
        "itm_dielectric_constant",
        "itm_conductivity_s_per_m",
        "itm_confidence",
        "itm_reliability",
    )

    missing_fields = [
        field
        for field in required_fields
        if coverage_run.get(
            field
        ) is None
    ]

    if missing_fields:
        raise ValueError(
            "Coverage run is missing required fields: "
            + ", ".join(
                missing_fields
            )
        )

    _validate_clutter_configuration(
        coverage_run
    )


def _validate_clutter_configuration(
    coverage_run: dict[str, Any],
) -> None:
    """Validate optional clutter dataset and model snapshot."""

    field_names = (
        "clutter_source",
        "clutter_version",
        "clutter_model",
        "clutter_model_version",
        "clutter_percentage_locations",
        "clutter_correction_end",
    )

    values = [
        coverage_run.get(
            field_name
        )
        for field_name in field_names
    ]

    clutter_requested = any(
        value is not None
        for value in values
    )

    if not clutter_requested:
        return

    missing_fields = [
        field_name
        for field_name in field_names
        if coverage_run.get(
            field_name
        ) is None
    ]

    if missing_fields:
        raise ValueError(
            "Coverage run has incomplete clutter parameters: "
            + ", ".join(
                missing_fields
            )
        )

    clutter_model = str(
        coverage_run[
            "clutter_model"
        ]
    )

    clutter_model_version = str(
        coverage_run[
            "clutter_model_version"
        ]
    )

    clutter_correction_end = str(
        coverage_run[
            "clutter_correction_end"
        ]
    )

    if (
        clutter_model
        != P2108_CLUTTER_MODEL
    ):
        raise ValueError(
            "Unsupported clutter model: "
            f"{clutter_model!r}."
        )

    if (
        clutter_model_version
        != P2108_CLUTTER_MODEL_VERSION
    ):
        raise ValueError(
            "Unsupported clutter model version: "
            f"{clutter_model_version!r}."
        )

    percentage_locations = float(
        coverage_run[
            "clutter_percentage_locations"
        ]
    )

    if (
        not math.isfinite(
            percentage_locations
        )
        or percentage_locations <= 0
        or percentage_locations >= 100
    ):
        raise ValueError(
            "Clutter percentage of locations must be "
            "greater than 0 and less than 100."
        )

    if (
        clutter_correction_end
        != P2108_CORRECTION_END
    ):
        raise ValueError(
            "Current GeoVaris coverage calculations support "
            "receiver-side P.2108 clutter correction only."
        )


def _run_uses_clutter(
    coverage_run: dict[str, Any],
) -> bool:
    """Return True when the immutable run snapshot enables clutter."""

    return (
        coverage_run.get(
            "clutter_model"
        )
        is not None
    )


def _build_itm_configuration(
    coverage_run: dict[str, Any],
) -> ItmConfiguration:
    """Build the typed ITM configuration from the run snapshot."""

    return ItmConfiguration(
        climate=ItmClimate(
            int(
                coverage_run[
                    "itm_climate"
                ]
            )
        ),
        polarization=ItmPolarization(
            int(
                coverage_run[
                    "itm_polarization"
                ]
            )
        ),
        variability_mode=ItmVariabilityMode(
            int(
                coverage_run[
                    "itm_variability_mode"
                ]
            )
        ),
        surface_refractivity_n_units=float(
            coverage_run[
                "itm_surface_refractivity"
            ]
        ),
        ground_dielectric_constant=float(
            coverage_run[
                "itm_dielectric_constant"
            ]
        ),
        ground_conductivity_s_per_m=float(
            coverage_run[
                "itm_conductivity_s_per_m"
            ]
        ),
        confidence=float(
            coverage_run[
                "itm_confidence"
            ]
        ),
        reliability=float(
            coverage_run[
                "itm_reliability"
            ]
        ),
    )


def _read_geojson_geometry(
    geojson_path: Path,
) -> dict[str, Any]:
    """Read and combine generated coverage Polygon/MultiPolygon features."""

    document = json.loads(
        geojson_path.read_text(
            encoding="utf-8"
        )
    )

    features = document.get(
        "features"
    )

    if (
        not isinstance(
            features,
            list,
        )
        or len(
            features
        )
        == 0
    ):
        raise ValueError(
            "Coverage GeoJSON must contain at least one feature."
        )

    polygons: list[
        list[Any]
    ] = []

    for index, feature in enumerate(
        features
    ):
        if not isinstance(
            feature,
            dict,
        ):
            raise ValueError(
                "Coverage GeoJSON feature "
                f"{index} is not a valid object."
            )

        geometry = feature.get(
            "geometry"
        )

        if not isinstance(
            geometry,
            dict,
        ):
            raise ValueError(
                "Coverage GeoJSON feature "
                f"{index} does not contain a valid geometry."
            )

        geometry_type = geometry.get(
            "type"
        )

        coordinates = geometry.get(
            "coordinates"
        )

        if geometry_type == "Polygon":
            if not isinstance(
                coordinates,
                list,
            ):
                raise ValueError(
                    "Coverage Polygon feature "
                    f"{index} has invalid coordinates."
                )

            polygons.append(
                coordinates
            )

        elif geometry_type == "MultiPolygon":
            if not isinstance(
                coordinates,
                list,
            ):
                raise ValueError(
                    "Coverage MultiPolygon feature "
                    f"{index} has invalid coordinates."
                )

            polygons.extend(
                coordinates
            )

        else:
            raise ValueError(
                "Coverage GeoJSON contains unsupported geometry "
                f"type {geometry_type!r}."
            )

    if not polygons:
        raise ValueError(
            "Coverage GeoJSON contains no polygon geometry."
        )

    if len(polygons) == 1:
        return {
            "type": "Polygon",
            "coordinates": (
                polygons[0]
            ),
        }

    return {
        "type": "MultiPolygon",
        "coordinates": polygons,
    }


def complete_itm_run(
    connection: psycopg.Connection,
    *,
    run_id: Any,
    coverage_raster_uri: str,
    coverage_geometry: dict[str, Any],
    processing_time_seconds: float,
) -> None:
    """Store the completed ITM result and derived analytics."""

    geometry_json = json.dumps(
        coverage_geometry
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs

            SET
                status = 'completed',
                completed_at = NOW(),

                coverage_raster_uri = %s,

                coverage_geometry =
                    ST_Multi(
                        ST_SetSRID(
                            ST_GeomFromGeoJSON(%s),
                            4326
                        )
                    ),

                coverage_area_sq_m =
                    ST_Area(
                        ST_SetSRID(
                            ST_GeomFromGeoJSON(%s),
                            4326
                        )::geography
                    ),

                processing_time_seconds = %s,
                error_message = NULL

            WHERE id = %s;
            """,
            (
                coverage_raster_uri,
                geometry_json,
                geometry_json,
                processing_time_seconds,
                run_id,
            ),
        )

    connection.commit()


def fail_itm_run(
    connection: psycopg.Connection,
    *,
    run_id: Any,
    error_message: str,
) -> None:
    """Mark an ITM run failed while preserving its failure reason."""

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                status = 'failed',
                completed_at = NOW(),
                error_message = %s
            WHERE id = %s;
            """,
            (
                error_message[
                    :2000
                ],
                run_id,
            ),
        )

    connection.commit()


def process_one_itm_run() -> bool:
    """Claim and process one pending NTIA ITM coverage run."""

    database_url = (
        get_database_url()
    )

    dem_raster_path = (
        get_dem_raster_path()
    )

    output_root = (
        get_output_root()
    )

    requested_run_id = (
        get_requested_run_id()
    )

    if requested_run_id is not None:
        print(
            "Requested coverage run: "
            f"{requested_run_id}"
        )

    with psycopg.connect(
        database_url
    ) as connection:
        coverage_run = (
            claim_pending_itm_run(
                connection
            )
        )

        if coverage_run is None:
            if requested_run_id is None:
                print(
                    "No pending ntia_itm coverage runs found."
                )
            else:
                print(
                    "Requested coverage run was not found, "
                    "is not pending, or is not an ntia_itm run: "
                    f"{requested_run_id}"
                )

            return False

        run_id = (
            coverage_run[
                "id"
            ]
        )

        print(
            f"Processing NTIA ITM coverage run {run_id}"
        )

        started = (
            time.perf_counter()
        )

        try:
            _validate_run(
                coverage_run
            )

            clutter_raster_path: Path | None = None

            if _run_uses_clutter(
                coverage_run
            ):
                clutter_raster_path = (
                    get_clutter_raster_path()
                )

            terrain_sample_spacing_m = (
                _terrain_sample_spacing_m(
                    dem_raster_path
                )
            )

            configuration = (
                _build_itm_configuration(
                    coverage_run
                )
            )

            model = ItmModel(
                dll_path=(
                    default_local_itm_dll_path()
                ),
                configuration=configuration,
                model_version=MODEL_VERSION,
            )

            grid = (
                plan_coverage_grid(
                    site_latitude=float(
                        coverage_run[
                            "site_latitude"
                        ]
                    ),
                    site_longitude=float(
                        coverage_run[
                            "site_longitude"
                        ]
                    ),
                    radius_m=float(
                        coverage_run[
                            "calculation_radius_m"
                        ]
                    ),
                    resolution_m=float(
                        coverage_run[
                            "resolution_m"
                        ]
                    ),
                )
            )

            propagation_cell_count = sum(
                1
                for point in grid.points
                if (
                    point.inside_radius
                    and point.distance_from_site_m
                    > 0.0
                )
            )

            if propagation_cell_count <= 0:
                raise ValueError(
                    "Coverage grid contains no propagation cells."
                )

            eirp_dbm = (
                _watts_to_dbm(
                    float(
                        coverage_run[
                            "eirp_watts"
                        ]
                    )
                )
            )

            clutter_percentage_locations = (
                None
            )

            if _run_uses_clutter(
                coverage_run
            ):
                clutter_percentage_locations = float(
                    coverage_run[
                        "clutter_percentage_locations"
                    ]
                )

            calculation_kwargs: dict[
                str,
                Any,
            ] = {
                "model": model,
                "grid": grid,
                "dem_raster_path": str(
                    dem_raster_path
                ),
                "frequency_mhz": float(
                    coverage_run[
                        "frequency_mhz"
                    ]
                ),
                "transmitter_height_agl_m": float(
                    coverage_run[
                        "antenna_height_m"
                    ]
                ),
                "receiver_height_agl_m": float(
                    coverage_run[
                        "receiver_height_m"
                    ]
                ),
                "terrain_sample_spacing_m": (
                    terrain_sample_spacing_m
                ),
                "eirp_dbm": eirp_dbm,

                # The stored antenna_gain_dbi is a transmitter
                # parameter. EIRP already includes transmit gain,
                # so it must not be added again here.
                "receiver_gain_dbi": 0.0,

                # No separate system-loss field exists in the
                # current scenario contract yet.
                "additional_losses_db": 0.0,

                "receiver_threshold_dbm": float(
                    coverage_run[
                        "receiver_threshold_dbm"
                    ]
                ),
                "max_propagation_cells": (
                    propagation_cell_count
                ),
            }

            if clutter_raster_path is not None:
                calculation_kwargs[
                    "clutter_raster_path"
                ] = str(
                    clutter_raster_path
                )

                calculation_kwargs[
                    "clutter_percentage_locations"
                ] = (
                    clutter_percentage_locations
                )

            calculation = (
                calculate_coverage_subset(
                    **calculation_kwargs
                )
            )

            artifacts = (
                build_coverage_artifact_paths(
                    output_root=output_root,
                    run_id=run_id,
                )
            )

            artifacts.raster_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            raster_path = (
                artifacts.raster_path
            )

            geojson_path = (
                artifacts.geojson_path
            )

            write_coverage_geotiff(
                grid=grid,
                calculation=calculation,
                output_path=str(
                    raster_path
                ),
            )

            coverage_raster_to_geojson(
                raster_path=str(
                    raster_path
                ),
                output_path=str(
                    geojson_path
                ),
            )

            coverage_geometry = (
                _read_geojson_geometry(
                    geojson_path
                )
            )

            storage = (
                LocalCoverageStorage()
            )

            coverage_raster_uri = (
                storage.publish(
                    local_path=raster_path,
                    artifact_key=(
                        artifacts.raster_key
                    ),
                )
            )

            storage.publish(
                local_path=geojson_path,
                artifact_key=(
                    artifacts.geojson_key
                ),
            )

            processing_time_seconds = (
                time.perf_counter()
                - started
            )

            complete_itm_run(
                connection,
                run_id=run_id,
                coverage_raster_uri=(
                    coverage_raster_uri
                ),
                coverage_geometry=(
                    coverage_geometry
                ),
                processing_time_seconds=(
                    processing_time_seconds
                ),
            )

            print(
                f"Completed NTIA ITM run {run_id}"
            )

            print(
                f"Grid: {grid.width} x {grid.height}"
            )

            print(
                "Propagation cells: "
                f"{propagation_cell_count}"
            )

            print(
                "Terrain sample spacing: "
                f"{terrain_sample_spacing_m:.2f} m"
            )

            if clutter_raster_path is not None:
                print(
                    "Clutter dataset: "
                    f"{coverage_run['clutter_source']} "
                    f"{coverage_run['clutter_version']}"
                )

                print(
                    "Clutter model: "
                    f"{coverage_run['clutter_model']} "
                    f"{coverage_run['clutter_model_version']}"
                )

                print(
                    "Clutter percentage locations: "
                    f"{clutter_percentage_locations:.2f}"
                )

                print(
                    "Clutter correction end: "
                    f"{coverage_run['clutter_correction_end']}"
                )

            print(
                f"GeoTIFF: {raster_path.resolve()}"
            )

            print(
                f"GeoJSON: {geojson_path.resolve()}"
            )

            print(
                "Processing time: "
                f"{processing_time_seconds:.2f} s"
            )

            return True

        except Exception as exc:
            fail_itm_run(
                connection,
                run_id=run_id,
                error_message=str(
                    exc
                ),
            )

            print(
                f"NTIA ITM coverage run {run_id} "
                f"failed: {exc}",
                file=sys.stderr,
            )

            raise


if __name__ == "__main__":
    process_one_itm_run()