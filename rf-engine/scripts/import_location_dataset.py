from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class ColumnMapping:
    location_id: str
    latitude: str
    longitude: str


@dataclass(frozen=True)
class ImportConfig:
    csv_path: Path
    customer_id: str
    dataset_name: str
    dataset_type: str
    source_name: str
    source_version: str | None
    effective_date: date | None
    acquisition_date: date | None
    is_mock: bool
    crs_epsg: int
    mapping: ColumnMapping


def parse_date(value: str | None) -> date | None:
    if not value:
        return None

    return datetime.strptime(
        value,
        "%Y-%m-%d",
    ).date()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for chunk in iter(
            lambda: file_handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_headers(
    fieldnames: list[str] | None,
    mapping: ColumnMapping,
) -> None:
    if not fieldnames:
        raise ValueError(
            "CSV does not contain a header row.",
        )

    required_columns = {
        mapping.location_id,
        mapping.latitude,
        mapping.longitude,
    }

    missing_columns = sorted(
        required_columns - set(fieldnames),
    )

    if missing_columns:
        raise ValueError(
            "CSV is missing required mapped columns: "
            + ", ".join(missing_columns),
        )


def parse_point_row(
    row: dict[str, str],
    mapping: ColumnMapping,
) -> tuple[
    str,
    float,
    float,
    dict[str, Any],
]:
    source_location_id = (
        row.get(mapping.location_id, "") or ""
    ).strip()

    if not source_location_id:
        raise ValueError(
            "Mapped location ID is empty.",
        )

    latitude_text = (
        row.get(mapping.latitude, "") or ""
    ).strip()

    longitude_text = (
        row.get(mapping.longitude, "") or ""
    ).strip()

    try:
        latitude = float(latitude_text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid latitude: {latitude_text!r}",
        ) from exc

    try:
        longitude = float(longitude_text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid longitude: {longitude_text!r}",
        ) from exc

    if not -90 <= latitude <= 90:
        raise ValueError(
            f"Latitude out of range: {latitude}",
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            f"Longitude out of range: {longitude}",
        )

    mapped_source_columns = {
        mapping.location_id,
        mapping.latitude,
        mapping.longitude,
    }

    source_attributes = {
        key: value
        for key, value in row.items()
        if (
            key not in mapped_source_columns
            and value not in (None, "")
        )
    }

    return (
        source_location_id,
        latitude,
        longitude,
        source_attributes,
    )


def create_dataset_record(
    connection: psycopg.Connection,
    config: ImportConfig,
    file_sha256: str,
) -> str:
    column_mapping = {
        "location_id":
            config.mapping.location_id,

        "latitude":
            config.mapping.latitude,

        "longitude":
            config.mapping.longitude,
    }

    metadata = {
        "import_method":
            "GeoVaris configurable CSV importer",
    }

    with connection.cursor(
        row_factory=dict_row,
    ) as cursor:
        cursor.execute(
            """
            INSERT INTO location_datasets (
                customer_id,
                name,
                dataset_type,
                source_name,
                source_version,
                effective_date,
                acquisition_date,
                crs_epsg,
                is_mock,
                original_filename,
                source_file_sha256,
                column_mapping,
                metadata,
                quality_status,
                import_status
            )
            VALUES (
                %(customer_id)s,
                %(name)s,
                %(dataset_type)s,
                %(source_name)s,
                %(source_version)s,
                %(effective_date)s,
                %(acquisition_date)s,
                %(crs_epsg)s,
                %(is_mock)s,
                %(original_filename)s,
                %(source_file_sha256)s,
                %(column_mapping)s::jsonb,
                %(metadata)s::jsonb,
                'unverified',
                'importing'
            )
            RETURNING id;
            """,
            {
                "customer_id":
                    config.customer_id,

                "name":
                    config.dataset_name,

                "dataset_type":
                    config.dataset_type,

                "source_name":
                    config.source_name,

                "source_version":
                    config.source_version,

                "effective_date":
                    config.effective_date,

                "acquisition_date":
                    config.acquisition_date,

                "crs_epsg":
                    config.crs_epsg,

                "is_mock":
                    config.is_mock,

                "original_filename":
                    config.csv_path.name,

                "source_file_sha256":
                    file_sha256,

                "column_mapping":
                    json.dumps(
                        column_mapping,
                    ),

                "metadata":
                    json.dumps(
                        metadata,
                    ),
            },
        )

        row = cursor.fetchone()

        if not row:
            raise RuntimeError(
                "Dataset registration failed.",
            )

        return str(
            row["id"],
        )


def import_points(
    connection: psycopg.Connection,
    dataset_id: str,
    config: ImportConfig,
) -> int:
    imported_count = 0

    with config.csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        reader = csv.DictReader(
            csv_file,
        )

        validate_headers(
            reader.fieldnames,
            config.mapping,
        )

        with connection.cursor() as cursor:
            for line_number, row in enumerate(
                reader,
                start=2,
            ):
                try:
                    (
                        source_location_id,
                        latitude,
                        longitude,
                        source_attributes,
                    ) = parse_point_row(
                        row,
                        config.mapping,
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"CSV line {line_number}: {exc}",
                    ) from exc

                cursor.execute(
                    """
                    INSERT INTO location_dataset_points (
                        dataset_id,
                        source_location_id,
                        latitude,
                        longitude,
                        location,
                        source_attributes
                    )
                    VALUES (
                        %(dataset_id)s,
                        %(source_location_id)s,
                        %(latitude)s,
                        %(longitude)s,
                        ST_SetSRID(
                            ST_MakePoint(
                                %(longitude)s,
                                %(latitude)s
                            ),
                            4326
                        ),
                        %(source_attributes)s::jsonb
                    );
                    """,
                    {
                        "dataset_id":
                            dataset_id,

                        "source_location_id":
                            source_location_id,

                        "latitude":
                            latitude,

                        "longitude":
                            longitude,

                        "source_attributes":
                            json.dumps(
                                source_attributes,
                            ),
                    },
                )

                imported_count += 1

    return imported_count


def mark_dataset_ready(
    connection: psycopg.Connection,
    dataset_id: str,
    row_count: int,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE location_datasets
            SET
                row_count = %(row_count)s,
                import_status = 'ready',
                imported_at = NOW(),
                updated_at = NOW()
            WHERE id = %(dataset_id)s;
            """,
            {
                "row_count":
                    row_count,

                "dataset_id":
                    dataset_id,
            },
        )


def mark_dataset_failed(
    connection: psycopg.Connection,
    dataset_id: str,
    error_message: str,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE location_datasets
            SET
                import_status = 'failed',
                metadata =
                    metadata ||
                    jsonb_build_object(
                        'import_error',
                        %(error_message)s
                    ),
                updated_at = NOW()
            WHERE id = %(dataset_id)s;
            """,
            {
                "dataset_id":
                    dataset_id,

                "error_message":
                    error_message,
            },
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import a configurable CSV point dataset "
            "into GeoVaris Coverage Intelligence."
        ),
    )

    parser.add_argument(
        "--csv",
        required=True,
    )

    parser.add_argument(
        "--customer-id",
        required=True,
    )

    parser.add_argument(
        "--dataset-name",
        required=True,
    )

    parser.add_argument(
        "--dataset-type",
        required=True,
        choices=[
            "mock_fcc_fabric",
            "fcc_fabric",
            "customer_locations",
            "other",
        ],
    )

    parser.add_argument(
        "--source-name",
        required=True,
    )

    parser.add_argument(
        "--source-version",
    )

    parser.add_argument(
        "--effective-date",
    )

    parser.add_argument(
        "--acquisition-date",
    )

    parser.add_argument(
        "--crs-epsg",
        type=int,
        default=4326,
    )

    parser.add_argument(
        "--mock",
        action="store_true",
    )

    parser.add_argument(
        "--location-id-column",
        required=True,
    )

    parser.add_argument(
        "--latitude-column",
        required=True,
    )

    parser.add_argument(
        "--longitude-column",
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    database_url = os.environ.get(
        "DATABASE_URL",
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured.",
        )

    csv_path = Path(
        args.csv,
    ).expanduser().resolve()

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file was not found: {csv_path}",
        )

    config = ImportConfig(
        csv_path=
            csv_path,

        customer_id=
            args.customer_id,

        dataset_name=
            args.dataset_name,

        dataset_type=
            args.dataset_type,

        source_name=
            args.source_name,

        source_version=
            args.source_version,

        effective_date=
            parse_date(
                args.effective_date,
            ),

        acquisition_date=
            parse_date(
                args.acquisition_date,
            ),

        is_mock=
            args.mock,

        crs_epsg=
            args.crs_epsg,

        mapping=
            ColumnMapping(
                location_id=
                    args.location_id_column,

                latitude=
                    args.latitude_column,

                longitude=
                    args.longitude_column,
            ),
    )

    if config.crs_epsg != 4326:
        raise ValueError(
            "The current importer requires source "
            "latitude/longitude coordinates in EPSG:4326. "
            "Reprojection support will be added separately."
        )

    file_sha256 = sha256_file(
        config.csv_path,
    )

    dataset_id: str | None = None
    row_count = 0

    # Register the dataset first and commit it so an
    # import failure can be recorded against a durable
    # governed dataset record.
    with psycopg.connect(
        database_url,
    ) as connection:
        dataset_id = create_dataset_record(
            connection,
            config,
            file_sha256,
        )

        connection.commit()

    try:
        with psycopg.connect(
            database_url,
        ) as connection:
            row_count = import_points(
                connection,
                dataset_id,
                config,
            )

            mark_dataset_ready(
                connection,
                dataset_id,
                row_count,
            )

            connection.commit()

    except Exception as exc:
        with psycopg.connect(
            database_url,
        ) as failure_connection:
            mark_dataset_failed(
                failure_connection,
                dataset_id,
                str(exc),
            )

            failure_connection.commit()

        raise

    print(
        "Location dataset import complete.",
    )

    print(
        f"Dataset ID: {dataset_id}",
    )

    print(
        f"Rows imported: {row_count}",
    )

    print(
        f"SHA-256: {file_sha256}",
    )


if __name__ == "__main__":
    main()