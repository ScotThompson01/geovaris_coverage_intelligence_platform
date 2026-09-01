"""GeoVaris Rapid Coverage development worker.

Processes one pending ``rapid_coverage`` coverage run using:

- immutable RF inputs stored on coverage_runs
- an explicitly configured local DEM raster
- an explicitly configured Annual NLCD raster
- the governed GeoVaris clutter-height profile
- DEM + clutter effective-surface generation
- curvature-adjusted GDAL terrain/clutter viewshed
- free-space link-budget range
- Rapid Coverage raster intersection
- display-filtered GeoJSON
- stable coverage artifact paths
- PostGIS run completion
- PostGIS population analytics during run completion

For development/testing, GEOVARIS_COVERAGE_RUN_ID may be set to
explicitly select one pending Rapid Coverage run. When it is not set,
the oldest pending Rapid Coverage run is processed.

This is an MVP development worker. It is not yet the final production
job-queue or object-storage implementation.

Rapid Coverage results are engineering estimates and do not guarantee
actual service availability.
"""

from __future__ import annotations

import math
import os
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from geovaris_rf.artifacts import (
    build_coverage_artifact_paths,
)
from geovaris_rf.clutter_height import (
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME,
    GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION,
    build_geovaris_default_clutter_height_profile,
)
from geovaris_rf.effective_surface import (
    build_effective_surface_raster,
)
from geovaris_rf.free_space import (
    watts_to_dbm,
)
from geovaris_rf.rapid_coverage import (
    build_rapid_coverage_raster,
)
from geovaris_rf.rapid_coverage_geojson import (
    rapid_coverage_raster_to_geojson,
)
from geovaris_rf.rapid_run_completion import (
    RAPID_PROPAGATION_MODEL,
    RAPID_PROPAGATION_MODEL_VERSION,
    complete_rapid_run,
)
from geovaris_rf.storage import (
    LocalCoverageStorage,
)
from geovaris_rf.viewshed import (
    build_viewshed_raster,
)


DEM_ENVIRONMENT_VARIABLE = (
    "GEOVARIS_RAPID_DEM_RASTER_PATH"
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

RAPID_RESOLUTION_M = 30.0

RAPID_CLUTTER_SOURCE = (
    "USGS/MRLC Annual NLCD Land Cover"
)

RAPID_CLUTTER_VERSION = (
    "2025 C1V2"
)

RAPID_DEM_SOURCE = (
    "GeoVaris TEST-002 working DEM"
)

RAPID_DEM_VERSION = (
    "test002_60km_30m_utm17"
)

RAPID_DEM_HORIZONTAL_CRS = (
    "EPSG:32617"
)

RAPID_DEM_VERTICAL_DATUM = (
    "unknown"
)

RAPID_DEM_UNITS = (
    "m"
)

RAPID_DEM_RESOLUTION_M = (
    30.0
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
    """Resolve one explicitly configured local working file."""

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
    """Resolve the Rapid working DEM raster."""

    return _resolve_required_file(
        environment_variable=(
            DEM_ENVIRONMENT_VARIABLE
        ),
        description=(
            "Rapid Coverage DEM raster"
        ),
    )


def get_clutter_raster_path() -> Path:
    """Resolve the Annual NLCD clutter raster."""

    return _resolve_required_file(
        environment_variable=(
            CLUTTER_ENVIRONMENT_VARIABLE
        ),
        description=(
            "Rapid Coverage NLCD clutter raster"
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


def claim_pending_rapid_run(
    connection: psycopg.Connection,
) -> dict[str, Any] | None:
    """Claim one pending Rapid Coverage run.

    When GEOVARIS_COVERAGE_RUN_ID is configured, only that pending
    Rapid Coverage run is eligible. Otherwise the oldest pending
    Rapid Coverage run is claimed.

    Row locking prevents two workers from claiming the same run.
    """

    requested_run_id = (
        get_requested_run_id()
    )

    select_columns = """
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
    """

    with connection.transaction():
        with connection.cursor(
            row_factory=dict_row
        ) as cursor:
            if requested_run_id is None:
                cursor.execute(
                    f"""
                    SELECT
                        {select_columns}

                    FROM coverage_runs

                    WHERE status = 'pending'
                      AND propagation_model = %s

                    ORDER BY created_at

                    FOR UPDATE SKIP LOCKED

                    LIMIT 1;
                    """,
                    (
                        RAPID_PROPAGATION_MODEL,
                    ),
                )
            else:
                cursor.execute(
                    f"""
                    SELECT
                        {select_columns}

                    FROM coverage_runs

                    WHERE id = %s
                      AND status = 'pending'
                      AND propagation_model = %s

                    FOR UPDATE SKIP LOCKED

                    LIMIT 1;
                    """,
                    (
                        requested_run_id,
                        RAPID_PROPAGATION_MODEL,
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

            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Rapid coverage run could not be marked processing."
                )

            return dict(
                coverage_run
            )


def snapshot_rapid_dem_lineage(
    connection: psycopg.Connection,
    *,
    coverage_run: dict[str, Any],
) -> None:
    """Snapshot governed Rapid DEM lineage onto a coverage run.

    The current development worker uses the explicitly governed
    TEST-002 working DEM. These values describe that working raster
    without claiming an upstream source/version that has not yet
    been verified.

    The in-memory immutable run snapshot is updated at the same time
    as the database record so later validation and logging use the
    same lineage values.
    """

    run_id = coverage_run.get(
        "id"
    )

    if run_id is None:
        raise ValueError(
            "Coverage run is missing required field: id"
        )

    coverage_run[
        "dem_source"
    ] = RAPID_DEM_SOURCE

    coverage_run[
        "dem_version"
    ] = RAPID_DEM_VERSION

    coverage_run[
        "dem_horizontal_crs"
    ] = RAPID_DEM_HORIZONTAL_CRS

    coverage_run[
        "dem_vertical_datum"
    ] = RAPID_DEM_VERTICAL_DATUM

    coverage_run[
        "dem_units"
    ] = RAPID_DEM_UNITS

    coverage_run[
        "dem_resolution_m"
    ] = RAPID_DEM_RESOLUTION_M

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE coverage_runs
            SET
                dem_source = %s,
                dem_version = %s,
                dem_horizontal_crs = %s,
                dem_vertical_datum = %s,
                dem_units = %s,
                dem_resolution_m = %s
            WHERE id = %s;
            """,
            (
                RAPID_DEM_SOURCE,
                RAPID_DEM_VERSION,
                RAPID_DEM_HORIZONTAL_CRS,
                RAPID_DEM_VERTICAL_DATUM,
                RAPID_DEM_UNITS,
                RAPID_DEM_RESOLUTION_M,
                run_id,
            ),
        )

        if cursor.rowcount != 1:
            raise RuntimeError(
                "Rapid Coverage DEM lineage could not be "
                "snapshotted to the coverage run."
            )

    connection.commit()


def _validate_positive_number(
    coverage_run: dict[str, Any],
    *,
    field_name: str,
) -> float:
    """Validate one required finite positive run field."""

    value = coverage_run.get(
        field_name
    )

    if value is None:
        raise ValueError(
            "Coverage run is missing required field: "
            f"{field_name}"
        )

    numeric_value = float(
        value
    )

    if (
        not math.isfinite(
            numeric_value
        )
        or numeric_value <= 0
    ):
        raise ValueError(
            f"{field_name} must be finite "
            "and greater than zero."
        )

    return numeric_value


def _validate_finite_number(
    coverage_run: dict[str, Any],
    *,
    field_name: str,
) -> float:
    """Validate one required finite numeric run field."""

    value = coverage_run.get(
        field_name
    )

    if value is None:
        raise ValueError(
            "Coverage run is missing required field: "
            f"{field_name}"
        )

    numeric_value = float(
        value
    )

    if not math.isfinite(
        numeric_value
    ):
        raise ValueError(
            f"{field_name} must be finite."
        )

    return numeric_value


def _validate_run(
    coverage_run: dict[str, Any],
) -> None:
    """Validate one immutable Rapid Coverage run snapshot."""

    if (
        coverage_run.get(
            "propagation_model"
        )
        != RAPID_PROPAGATION_MODEL
    ):
        raise ValueError(
            "Coverage run is not a rapid_coverage run."
        )

    if (
        coverage_run.get(
            "propagation_model_version"
        )
        != RAPID_PROPAGATION_MODEL_VERSION
    ):
        raise ValueError(
            "Unsupported Rapid Coverage model version: "
            f"{coverage_run.get('propagation_model_version')!r}."
        )

    latitude = _validate_finite_number(
        coverage_run,
        field_name="site_latitude",
    )

    longitude = _validate_finite_number(
        coverage_run,
        field_name="site_longitude",
    )

    if (
        latitude < -90.0
        or latitude > 90.0
    ):
        raise ValueError(
            "site_latitude must be between -90 and 90."
        )

    if (
        longitude < -180.0
        or longitude > 180.0
    ):
        raise ValueError(
            "site_longitude must be between -180 and 180."
        )

    _validate_positive_number(
        coverage_run,
        field_name="frequency_mhz",
    )

    _validate_positive_number(
        coverage_run,
        field_name="eirp_watts",
    )

    _validate_positive_number(
        coverage_run,
        field_name="antenna_height_m",
    )

    receiver_height_m = (
        _validate_finite_number(
            coverage_run,
            field_name="receiver_height_m",
        )
    )

    if receiver_height_m < 0:
        raise ValueError(
            "receiver_height_m must be zero or greater."
        )

    _validate_finite_number(
        coverage_run,
        field_name="receiver_threshold_dbm",
    )

    _validate_positive_number(
        coverage_run,
        field_name="calculation_radius_m",
    )

    resolution_m = (
        _validate_positive_number(
            coverage_run,
            field_name="resolution_m",
        )
    )

    if not math.isclose(
        resolution_m,
        RAPID_RESOLUTION_M,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Rapid Coverage development runs require "
            f"{RAPID_RESOLUTION_M:.0f} m resolution."
        )

    if (
        coverage_run.get(
            "clutter_source"
        )
        != RAPID_CLUTTER_SOURCE
    ):
        raise ValueError(
            "Unsupported Rapid Coverage clutter source: "
            f"{coverage_run.get('clutter_source')!r}."
        )

    if (
        coverage_run.get(
            "clutter_version"
        )
        != RAPID_CLUTTER_VERSION
    ):
        raise ValueError(
            "Unsupported Rapid Coverage clutter version: "
            f"{coverage_run.get('clutter_version')!r}."
        )

    if (
        coverage_run.get(
            "clutter_model"
        )
        != GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_NAME
    ):
        raise ValueError(
            "Unsupported Rapid Coverage clutter model: "
            f"{coverage_run.get('clutter_model')!r}."
        )

    if (
        coverage_run.get(
            "clutter_model_version"
        )
        != GEOVARIS_DEFAULT_CLUTTER_HEIGHT_PROFILE_VERSION
    ):
        raise ValueError(
            "Unsupported Rapid Coverage clutter model version: "
            f"{coverage_run.get('clutter_model_version')!r}."
        )

    if (
        coverage_run.get(
            "dem_source"
        )
        != RAPID_DEM_SOURCE
    ):
        raise ValueError(
            "Unsupported Rapid Coverage DEM source: "
            f"{coverage_run.get('dem_source')!r}."
        )

    if (
        coverage_run.get(
            "dem_version"
        )
        != RAPID_DEM_VERSION
    ):
        raise ValueError(
            "Unsupported Rapid Coverage DEM version: "
            f"{coverage_run.get('dem_version')!r}."
        )

    if (
        coverage_run.get(
            "dem_horizontal_crs"
        )
        != RAPID_DEM_HORIZONTAL_CRS
    ):
        raise ValueError(
            "Unsupported Rapid Coverage DEM horizontal CRS: "
            f"{coverage_run.get('dem_horizontal_crs')!r}."
        )

    if (
        coverage_run.get(
            "dem_vertical_datum"
        )
        != RAPID_DEM_VERTICAL_DATUM
    ):
        raise ValueError(
            "Unsupported Rapid Coverage DEM vertical datum: "
            f"{coverage_run.get('dem_vertical_datum')!r}."
        )

    if (
        coverage_run.get(
            "dem_units"
        )
        != RAPID_DEM_UNITS
    ):
        raise ValueError(
            "Unsupported Rapid Coverage DEM units: "
            f"{coverage_run.get('dem_units')!r}."
        )

    dem_resolution_m = (
        _validate_positive_number(
            coverage_run,
            field_name="dem_resolution_m",
        )
    )

    if not math.isclose(
        dem_resolution_m,
        RAPID_DEM_RESOLUTION_M,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Rapid Coverage development DEM must have "
            f"{RAPID_DEM_RESOLUTION_M:.0f} m resolution."
        )

    itm_fields = (
        "itm_climate",
        "itm_polarization",
        "itm_variability_mode",
        "itm_surface_refractivity",
        "itm_dielectric_constant",
        "itm_conductivity_s_per_m",
        "itm_confidence",
        "itm_reliability",
    )

    unexpected_itm_fields = [
        field_name
        for field_name in itm_fields
        if coverage_run.get(
            field_name
        ) is not None
    ]

    if unexpected_itm_fields:
        raise ValueError(
            "Rapid Coverage run must not contain ITM assumptions: "
            + ", ".join(
                unexpected_itm_fields
            )
        )

    if (
        coverage_run.get(
            "clutter_percentage_locations"
        )
        is not None
    ):
        raise ValueError(
            "Rapid Coverage run must not contain "
            "P.2108 clutter percentage assumptions."
        )

    if (
        coverage_run.get(
            "clutter_correction_end"
        )
        is not None
    ):
        raise ValueError(
            "Rapid Coverage run must not contain "
            "P.2108 clutter correction assumptions."
        )


def fail_rapid_run(
    connection: psycopg.Connection,
    *,
    run_id: Any,
    error_message: str,
) -> None:
    """Mark a Rapid Coverage run failed."""

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
                str(
                    error_message
                )[
                    :2000
                ],
                run_id,
            ),
        )

    connection.commit()


def process_one_rapid_run() -> bool:
    """Claim and process one pending Rapid Coverage run."""

    database_url = (
        get_database_url()
    )

    dem_raster_path = (
        get_dem_raster_path()
    )

    clutter_raster_path = (
        get_clutter_raster_path()
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
            claim_pending_rapid_run(
                connection
            )
        )

        if coverage_run is None:
            if requested_run_id is None:
                print(
                    "No pending rapid_coverage coverage runs found."
                )
            else:
                print(
                    "Requested coverage run was not found, "
                    "is not pending, or is not a rapid_coverage run: "
                    f"{requested_run_id}"
                )

            return False

        run_id = coverage_run[
            "id"
        ]

        print(
            "Processing Rapid Coverage run "
            f"{run_id}"
        )

        started = (
            time.perf_counter()
        )

        try:
            print(
                "Snapshotting Rapid DEM lineage..."
            )

            snapshot_rapid_dem_lineage(
                connection,
                coverage_run=coverage_run,
            )

            _validate_run(
                coverage_run
            )

            clutter_profile = (
                build_geovaris_default_clutter_height_profile()
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

            effective_surface_path = (
                raster_path.parent
                / "effective_surface.tif"
            )

            viewshed_path = (
                raster_path.parent
                / "viewshed.tif"
            )

            print(
                "Building effective terrain/clutter surface..."
            )

            build_effective_surface_raster(
                dem_path=dem_raster_path,
                clutter_raster_path=(
                    clutter_raster_path
                ),
                destination_path=(
                    effective_surface_path
                ),
                clutter_profile=(
                    clutter_profile
                ),
            )

            print(
                "Building terrain/clutter viewshed..."
            )

            build_viewshed_raster(
                dem_path=dem_raster_path,
                effective_surface_path=(
                    effective_surface_path
                ),
                destination_path=(
                    viewshed_path
                ),
                observer_latitude=float(
                    coverage_run[
                        "site_latitude"
                    ]
                ),
                observer_longitude=float(
                    coverage_run[
                        "site_longitude"
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
                calculation_radius_m=float(
                    coverage_run[
                        "calculation_radius_m"
                    ]
                ),
            )

            eirp_dbm = watts_to_dbm(
                float(
                    coverage_run[
                        "eirp_watts"
                    ]
                )
            )

            print(
                "Applying free-space link budget..."
            )

            build_rapid_coverage_raster(
                viewshed_path=(
                    viewshed_path
                ),
                destination_path=(
                    raster_path
                ),
                observer_latitude=float(
                    coverage_run[
                        "site_latitude"
                    ]
                ),
                observer_longitude=float(
                    coverage_run[
                        "site_longitude"
                    ]
                ),
                frequency_mhz=float(
                    coverage_run[
                        "frequency_mhz"
                    ]
                ),
                eirp_dbm=(
                    eirp_dbm
                ),
                receiver_threshold_dbm=float(
                    coverage_run[
                        "receiver_threshold_dbm"
                    ]
                ),
                calculation_radius_m=float(
                    coverage_run[
                        "calculation_radius_m"
                    ]
                ),

                # EIRP already includes transmitter gain.
                receiver_gain_dbi=0.0,

                # Current scenario schema has no separate
                # additional system-loss field.
                additional_losses_db=0.0,
            )

            print(
                "Building display GeoJSON..."
            )

            geojson_result = (
                rapid_coverage_raster_to_geojson(
                    raster_path=(
                        raster_path
                    ),
                    output_path=(
                        geojson_path
                    ),
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

            print(
                "Dissolving display geometry "
                "and calculating population in PostGIS..."
            )

            complete_rapid_run(
                connection,
                run_id=run_id,
                coverage_raster_uri=(
                    coverage_raster_uri
                ),
                display_geojson_path=(
                    geojson_path
                ),
                authoritative_coverage_area_sq_m=(
                    geojson_result
                    .authoritative_covered_area_m2
                ),
                processing_time_seconds=(
                    processing_time_seconds
                ),
            )

            print(
                "Completed Rapid Coverage run "
                f"{run_id}"
            )

            print(
                "Methodology: "
                "Terrain/Clutter LOS + "
                "Free-Space Link Budget"
            )

            print(
                "Frequency: "
                f"{float(coverage_run['frequency_mhz']):.3f} MHz"
            )

            print(
                "EIRP: "
                f"{float(coverage_run['eirp_watts']):.3f} W"
            )

            print(
                "Calculation radius: "
                f"{float(coverage_run['calculation_radius_m']):.2f} m"
            )

            print(
                "Raster resolution: "
                f"{float(coverage_run['resolution_m']):.2f} m"
            )

            print(
                "Covered cells: "
                f"{geojson_result.covered_cell_count:,}"
            )

            print(
                "Authoritative area: "
                f"{geojson_result.authoritative_covered_area_km2:.3f} km2"
            )

            print(
                "Display features: "
                f"{geojson_result.feature_count:,}"
            )

            print(
                "Display retained area: "
                f"{geojson_result.display_retained_area_percent:.3f}%"
            )

            print(
                "Clutter profile: "
                f"{clutter_profile.name} "
                f"{clutter_profile.version}"
            )

            print(
                "DEM lineage: "
                f"{coverage_run['dem_source']} / "
                f"{coverage_run['dem_version']} / "
                f"{coverage_run['dem_horizontal_crs']} / "
                f"{coverage_run['dem_vertical_datum']} / "
                f"{coverage_run['dem_units']} / "
                f"{float(coverage_run['dem_resolution_m']):.0f} m"
            )

            print(
                f"GeoTIFF: {raster_path.resolve()}"
            )

            print(
                f"GeoJSON: {geojson_path.resolve()}"
            )

            print(
                "Processing time: "
                f"{processing_time_seconds:.3f} s"
            )

            return True

        except Exception as exc:
            try:
                connection.rollback()
            except Exception:
                pass

            fail_rapid_run(
                connection,
                run_id=run_id,
                error_message=str(
                    exc
                ),
            )

            print(
                "Rapid Coverage run failed: "
                f"{run_id}"
            )

            print(
                f"Error: {exc}"
            )

            raise


def main() -> int:
    """Run one Rapid Coverage job."""

    process_one_rapid_run()

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )