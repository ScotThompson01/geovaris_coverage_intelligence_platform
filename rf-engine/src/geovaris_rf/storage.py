"""GeoVaris coverage artifact storage backends.

The RF calculation pipeline writes artifacts to local working paths.
A storage backend is responsible for publishing those artifacts and
returning the stable URI/key that GeoVaris stores as artifact lineage.

The current backend is local development storage. Object storage can be
added later without changing RF calculation code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CoverageStorageBackend(
    Protocol
):
    """Storage contract for generated coverage artifacts."""

    def publish(
        self,
        *,
        local_path: Path,
        artifact_key: str,
    ) -> str:
        """Publish an artifact and return its stable URI/key."""
        ...


class LocalCoverageStorage:
    """Local development coverage-artifact backend.

    Files are already written beneath the configured local output root,
    so publishing is intentionally a validation step rather than a copy.

    The stable artifact key is returned for database persistence instead
    of a machine-specific absolute filesystem path.
    """

    def publish(
        self,
        *,
        local_path: Path,
        artifact_key: str,
    ) -> str:
        path = Path(
            local_path
        )

        if not path.exists():
            raise FileNotFoundError(
                "Coverage artifact does not exist: "
                f"{path}"
            )

        if not path.is_file():
            raise ValueError(
                "Coverage artifact path is not a file: "
                f"{path}"
            )

        artifact_key_text = (
            str(
                artifact_key
            )
            .strip()
        )

        if not artifact_key_text:
            raise ValueError(
                "artifact_key must not be empty."
            )

        if "\\" in artifact_key_text:
            raise ValueError(
                "artifact_key must use POSIX-style separators."
            )

        return artifact_key_text
        