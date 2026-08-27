"""GeoVaris coverage artifact identifiers and local paths.

Artifact keys provide stable, platform-independent identifiers suitable
for database storage and future object-storage backends.

Local filesystem paths are development-storage implementation details
and must not be treated as durable artifact identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


COVERAGE_ARTIFACT_NAMESPACE = "coverage-runs"
COVERAGE_RASTER_FILENAME = "coverage.tif"
COVERAGE_GEOJSON_FILENAME = "coverage.geojson"


@dataclass(frozen=True)
class CoverageArtifactPaths:
    """Stable artifact keys plus local development paths."""

    raster_key: str
    geojson_key: str

    raster_path: Path
    geojson_path: Path


def build_coverage_artifact_paths(
    *,
    output_root: Path,
    run_id: Any,
) -> CoverageArtifactPaths:
    """Build stable artifact keys and local development paths.

    Stable keys always use POSIX separators:

        coverage-runs/<run-id>/coverage.tif
        coverage-runs/<run-id>/coverage.geojson

    The local development backend intentionally preserves the existing
    directory layout:

        <output-root>/<run-id>/coverage.tif
        <output-root>/<run-id>/coverage.geojson
    """

    run_id_text = str(
        run_id
    ).strip()

    if not run_id_text:
        raise ValueError(
            "run_id must not be empty."
        )

    artifact_prefix = (
        PurePosixPath(
            COVERAGE_ARTIFACT_NAMESPACE
        )
        / run_id_text
    )

    local_run_directory = (
        Path(
            output_root
        )
        / run_id_text
    )

    return CoverageArtifactPaths(
        raster_key=str(
            artifact_prefix
            / COVERAGE_RASTER_FILENAME
        ),
        geojson_key=str(
            artifact_prefix
            / COVERAGE_GEOJSON_FILENAME
        ),
        raster_path=(
            local_run_directory
            / COVERAGE_RASTER_FILENAME
        ),
        geojson_path=(
            local_run_directory
            / COVERAGE_GEOJSON_FILENAME
        ),
    )