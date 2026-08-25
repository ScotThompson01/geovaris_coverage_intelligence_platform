"""DEM interfaces for GeoVaris Coverage Intelligence.

Terrain data is governed engineering input. DEM implementations must preserve
source, version, CRS, units, resolution, and vertical-reference metadata.

This module currently supports point ground-elevation lookup from the
USGS 3DEP Elevation ImageServer.

Full RF terrain analysis will later use cropped DEM rasters rather than
repeated point queries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


USGS_3DEP_IDENTIFY_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/identify"
)


@dataclass(frozen=True)
class DemMetadata:
    """Metadata describing the elevation dataset used."""

    source: str
    version: str
    horizontal_crs: str
    vertical_datum: str
    units: str
    resolution_m: float | None


@dataclass(frozen=True)
class GroundElevationResult:
    """Ground elevation returned for a geographic coordinate."""

    latitude: float
    longitude: float
    elevation_m: float
    metadata: DemMetadata


def validate_coordinate(latitude: float, longitude: float) -> None:
    """Validate WGS84 geographic latitude and longitude."""

    if not -90.0 <= latitude <= 90.0:
        raise ValueError(
            f"Latitude must be between -90 and 90 degrees; got {latitude}."
        )

    if not -180.0 <= longitude <= 180.0:
        raise ValueError(
            f"Longitude must be between -180 and 180 degrees; got {longitude}."
        )


def _find_visible_catalog_item(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return the catalog item selected by the ImageServer mosaic."""

    catalog_items = payload.get("catalogItems", {})
    features = catalog_items.get("features", [])
    visibilities = payload.get("catalogItemVisibilities", [])

    for index, visible in enumerate(visibilities):
        if visible and index < len(features):
            return features[index].get("attributes", {})

    return None


def get_usgs_ground_elevation(
    latitude: float,
    longitude: float,
    timeout_seconds: float = 20.0,
) -> GroundElevationResult:
    """Retrieve site ground elevation from the USGS 3DEP ImageServer.

    Requests a 1-meter pixel size. If a 1-meter source exists at the
    requested location, the ImageServer mosaic can select it. Returned
    catalog metadata is inspected so GeoVaris records the actual selected
    source rather than merely assuming a dataset.
    """

    validate_coordinate(latitude, longitude)

    geometry = {
        "x": longitude,
        "y": latitude,
        "spatialReference": {
            "wkid": 4326,
        },
    }

    params = {
        "geometry": httpx.QueryParams(
            {}
        ),  # placeholder replaced below
    }

    request_params = {
        "geometry": (
            f'{{"x":{longitude},"y":{latitude},'
            '"spatialReference":{"wkid":4326}}}'
        ),
        "geometryType": "esriGeometryPoint",
        "pixelSize": "1,1",
        "returnGeometry": "false",
        "returnCatalogItems": "true",
        "f": "json",
    }

    # local_address="0.0.0.0" forces an IPv4 socket. This is required
    # in development environments where the USGS IPv6 path is unreliable.
    transport = httpx.HTTPTransport(
        local_address="0.0.0.0",
        retries=2,
    )

    try:
        with httpx.Client(
            transport=transport,
            timeout=timeout_seconds,
            headers={
                "User-Agent": "GeoVaris-Coverage-Intelligence/0.1",
            },
        ) as client:
            response = client.get(
                USGS_3DEP_IDENTIFY_URL,
                params=request_params,
            )

            response.raise_for_status()
            payload = response.json()

    except httpx.HTTPError as exc:
        raise RuntimeError(
            f"USGS 3DEP elevation lookup failed: {exc}"
        ) from exc

    value = payload.get("value")

    if value in (None, "", "NoData"):
        raise RuntimeError(
            f"USGS 3DEP returned no elevation data for "
            f"{latitude}, {longitude}."
        )

    try:
        elevation_m = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"USGS 3DEP returned an invalid elevation value: {value!r}"
        ) from exc

    selected_item = _find_visible_catalog_item(payload)

    if selected_item is None:
        raise RuntimeError(
            "USGS 3DEP returned an elevation but did not identify "
            "the selected source dataset."
        )

    source = selected_item.get("Source") or "USGS"

    title = (
        selected_item.get("title")
        or selected_item.get("Name")
        or "USGS 3DEP"
    )

    publication_date = selected_item.get("pubdate")

    version = (
        f"{title}; published {publication_date}"
        if publication_date
        else title
    )

    vertical_datum = (
        selected_item.get("VerticalDatum")
        or "Unknown — source metadata required"
    )

    # We requested a 1 m pixel size. Confirm the selected source appears
    # to support that resolution before recording 1 m as the result.
    low_pixel_size = selected_item.get("LowPS")

    resolution_m = None

    if isinstance(low_pixel_size, (int, float)) and low_pixel_size <= 1.0:
        resolution_m = 1.0

    return GroundElevationResult(
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation_m,
        metadata=DemMetadata(
            source=source,
            version=version,
            horizontal_crs="Input: EPSG:4326; service: EPSG:3857",
            vertical_datum=vertical_datum,
            units="meters",
            resolution_m=resolution_m,
        ),
    )