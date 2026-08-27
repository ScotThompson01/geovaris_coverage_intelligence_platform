"""GeoVaris NTIA ITM development coverage worker.

Processes one pending ``ntia_itm`` coverage run using:

- immutable RF inputs stored on coverage_runs
- immutable ITM assumptions stored on coverage_runs
- an explicitly configured local working DEM raster
- the validated NTIA ITM 1.4 native library
- GeoVaris coverage-grid, GeoTIFF, and GeoJSON pipelines

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
from geovaris_rf.artifacts import (
    build_coverage_artifact_paths,
)
from geovaris_rf.storage import (
    LocalCoverageStorage,
)
PROPAGATION_MODEL = "ntia_itm"
MODEL_VERSION = "1.4"

DEM_ENVIRONMENT_VARIABLE = "GEOVARIS_ITM_DEM_RASTER_PATH"
OUTPUT_ROOT_ENVIRONMENT_VARIABLE = "GEOVARIS_COVERAGE_OUTPUT_DIR"

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


def get_dem_raster_path() -> Path:
    """Resolve the explicitly configured working DEM raster."""

    configured_path = os.getenv(
        DEM_ENVIRONMENT_VARIABLE
    )

    if not configured_path:
        raise RuntimeError(
            f"{DEM_ENVIRONMENT_VARIABLE} must be configured "
            "for NTIA ITM coverage processing."
        )

    path = Path(
        configured_path
    ).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            "Configured ITM DEM raster does not exist: "
            f"{path}"
        )

    if not path.is_file():
        raise ValueError(
            "Configured ITM DEM raster path is not a file: "
            f"{path}"
        )

    return path


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
        output_root = DEFAULT_OUTPUT_ROOT

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
        not math.isfinite(watts)
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
    """Claim the oldest pending NTIA ITM coverage run."""

    with connection.transaction():
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
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
    """Validate required NTIA ITM run fields."""

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
    """Read the single coverage geometry from generated GeoJSON."""

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
        != 1
    ):
        raise ValueError(
            "Expected exactly one coverage GeoJSON feature; "
            f"got {0 if not isinstance(features, list) else len(features)}."
        )

    geometry = features[0].get(
        "geometry"
    )

    if not isinstance(
        geometry,
        dict,
    ):
        raise ValueError(
            "Coverage GeoJSON feature does not contain "
            "a valid geometry."
        )

    return geometry


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

    with psycopg.connect(
        database_url
    ) as connection:
        coverage_run = (
            claim_pending_itm_run(
                connection
            )
        )

        if coverage_run is None:
            print(
                "No pending ntia_itm coverage runs found."
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

            calculation = (
                calculate_coverage_subset(
                    model=model,
                    grid=grid,
                    dem_raster_path=str(
                        dem_raster_path
                    ),
                    frequency_mhz=float(
                        coverage_run[
                            "frequency_mhz"
                        ]
                    ),
                    transmitter_height_agl_m=float(
                        coverage_run[
                            "antenna_height_m"
                        ]
                    ),
                    receiver_height_agl_m=float(
                        coverage_run[
                            "receiver_height_m"
                        ]
                    ),
                    terrain_sample_spacing_m=(
                        terrain_sample_spacing_m
                    ),
                    eirp_dbm=eirp_dbm,

                    # The stored antenna_gain_dbi is a transmitter
                    # parameter. EIRP already includes transmit gain,
                    # so it must not be added again here.
                    receiver_gain_dbi=0.0,

                    # No separate system-loss field exists in the
                    # current scenario contract yet.
                    additional_losses_db=0.0,

                    receiver_threshold_dbm=float(
                        coverage_run[
                            "receiver_threshold_dbm"
                        ]
                    ),
                    max_propagation_cells=(
                        propagation_cell_count
                    ),
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
    