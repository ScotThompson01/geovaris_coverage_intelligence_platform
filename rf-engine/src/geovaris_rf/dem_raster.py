"""DEM raster utilities for GeoVaris Coverage Intelligence.

Current scope:
- Validate calculation radius.
- Calculate local geographic DEM extents.
- Build USGS 3DEP export requests.
- Download local DEM rasters.
- Inspect DEM raster metadata and elevation statistics.
- Select local WGS84 UTM CRS.
- Plan exact-resolution projected RF terrain grids.
- Reproject DEMs into RF working grids.
- Split RF terrain grids into deterministic download tiles.
- Download individual USGS 3DEP terrain tiles.
- Mosaic aligned tiles into one RF terrain raster.
- Provide useful USGS service error messages.

RF results produced from these datasets are engineering estimates.
Terrain source resolution and lineage must remain distinguishable from
the RF working-grid resolution.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject

from geovaris_rf.dem import validate_coordinate


EARTH_RADIUS_M = 6_371_008.8

USGS_3DEP_EXPORT_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer/exportImage"
)

DEFAULT_DEM_NODATA = -9999.0


@dataclass(frozen=True)
class GeographicBoundingBox:
    """WGS84 geographic bounding box."""

    west: float
    south: float
    east: float
    north: float


@dataclass(frozen=True)
class DemExportResult:
    """Metadata returned by a USGS 3DEP export request."""

    href: str
    width: int
    height: int
    extent: dict[str, Any]


@dataclass(frozen=True)
class DemDownloadResult:
    """Metadata describing a downloaded DEM raster."""

    file_path: str
    size_bytes: int
    source_href: str


@dataclass(frozen=True)
class DemRasterInfo:
    """Validated metadata describing a local DEM raster."""

    file_path: str
    crs: str
    width: int
    height: int
    pixel_size_x: float
    pixel_size_y: float
    data_type: str
    nodata: float | None
    min_elevation_m: float
    max_elevation_m: float
    mean_elevation_m: float


@dataclass(frozen=True)
class TerrainGridPlan:
    """Projected terrain working grid for RF analysis."""

    target_crs: str
    center_x_m: float
    center_y_m: float
    west_m: float
    south_m: float
    east_m: float
    north_m: float
    resolution_m: float
    width_px: int
    height_px: int


@dataclass(frozen=True)
class DemTilePlan:
    """One rectangular tile within a terrain working grid."""

    row: int
    column: int
    target_crs: str
    west_m: float
    south_m: float
    east_m: float
    north_m: float
    resolution_m: float
    width_px: int
    height_px: int


@dataclass(frozen=True)
class DemReprojectionResult:
    """Metadata describing a reprojected DEM."""

    source_path: str
    destination_path: str
    source_crs: str
    target_crs: str
    resolution_m: float
    width_px: int
    height_px: int
    resampling_method: str


@dataclass(frozen=True)
class DemMosaicResult:
    """Metadata describing a completed DEM mosaic."""

    destination_path: str
    target_crs: str
    resolution_m: float
    width_px: int
    height_px: int
    tile_count: int
    nodata: float


def validate_radius(radius_m: float) -> None:
    """Validate a positive calculation radius."""

    if radius_m <= 0:
        raise ValueError(
            f"Radius must be greater than zero meters; got {radius_m}."
        )


def _validate_export_size(
    width_px: int,
    height_px: int,
) -> None:
    """Validate positive export dimensions."""

    if width_px <= 0:
        raise ValueError(
            f"width_px must be greater than zero; got {width_px}."
        )

    if height_px <= 0:
        raise ValueError(
            f"height_px must be greater than zero; got {height_px}."
        )


def calculate_geographic_bounding_box(
    latitude: float,
    longitude: float,
    radius_m: float,
) -> GeographicBoundingBox:
    """Calculate a WGS84 bounding box around a site."""

    validate_coordinate(
        latitude,
        longitude,
    )

    validate_radius(radius_m)

    latitude_rad = math.radians(latitude)
    angular_distance = radius_m / EARTH_RADIUS_M

    latitude_delta_deg = math.degrees(
        angular_distance
    )

    cosine_latitude = math.cos(latitude_rad)

    if abs(cosine_latitude) < 1e-12:
        longitude_delta_deg = 180.0
    else:
        longitude_delta_deg = math.degrees(
            angular_distance / cosine_latitude
        )

    south = max(
        -90.0,
        latitude - latitude_delta_deg,
    )

    north = min(
        90.0,
        latitude + latitude_delta_deg,
    )

    west = longitude - longitude_delta_deg
    east = longitude + longitude_delta_deg

    if west < -180.0:
        west += 360.0

    if east > 180.0:
        east -= 360.0

    return GeographicBoundingBox(
        west=west,
        south=south,
        east=east,
        north=north,
    )


def _build_3dep_export_params(
    bounds: GeographicBoundingBox,
    width_px: int,
    height_px: int,
    response_format: str,
) -> dict[str, str]:
    """Build a legacy WGS84-bound 3DEP export request."""

    _validate_export_size(
        width_px,
        height_px,
    )

    return {
        "bbox": (
            f"{bounds.west},"
            f"{bounds.south},"
            f"{bounds.east},"
            f"{bounds.north}"
        ),
        "bboxSR": "4326",
        "imageSR": "3857",
        "size": f"{width_px},{height_px}",
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "adjustAspectRatio": "true",
        "f": response_format,
    }


def _epsg_number_from_crs(
    target_crs: str,
) -> str:
    """Extract an EPSG number from an EPSG CRS string."""

    prefix = "EPSG:"

    if not target_crs.upper().startswith(prefix):
        raise ValueError(
            "Only EPSG target CRS strings are currently supported; "
            f"got {target_crs!r}."
        )

    epsg = target_crs[len(prefix):]

    if not epsg.isdigit():
        raise ValueError(
            f"Invalid EPSG CRS string: {target_crs!r}."
        )

    return epsg


def _build_3dep_grid_export_params(
    grid: TerrainGridPlan,
    response_format: str,
) -> dict[str, str]:
    """Build a 3DEP export request for an RF terrain grid."""

    _validate_export_size(
        grid.width_px,
        grid.height_px,
    )

    epsg = _epsg_number_from_crs(
        grid.target_crs
    )

    return {
        "bbox": (
            f"{grid.west_m},"
            f"{grid.south_m},"
            f"{grid.east_m},"
            f"{grid.north_m}"
        ),
        "bboxSR": epsg,
        "imageSR": epsg,
        "size": (
            f"{grid.width_px},"
            f"{grid.height_px}"
        ),
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "adjustAspectRatio": "false",
        "f": response_format,
    }


def _build_3dep_tile_export_params(
    tile: DemTilePlan,
    response_format: str,
) -> dict[str, str]:
    """Build a 3DEP export request for one RF terrain tile."""

    _validate_export_size(
        tile.width_px,
        tile.height_px,
    )

    epsg = _epsg_number_from_crs(
        tile.target_crs
    )

    return {
        "bbox": (
            f"{tile.west_m},"
            f"{tile.south_m},"
            f"{tile.east_m},"
            f"{tile.north_m}"
        ),
        "bboxSR": epsg,
        "imageSR": epsg,
        "size": (
            f"{tile.width_px},"
            f"{tile.height_px}"
        ),
        "format": "tiff",
        "pixelType": "F32",
        "interpolation": "RSP_BilinearInterpolation",
        "adjustAspectRatio": "false",
        "f": response_format,
    }


def build_3dep_export_url(
    bounds: GeographicBoundingBox,
    width_px: int,
    height_px: int,
) -> str:
    """Build a USGS 3DEP export metadata URL."""

    params = _build_3dep_export_params(
        bounds=bounds,
        width_px=width_px,
        height_px=height_px,
        response_format="json",
    )

    return (
        f"{USGS_3DEP_EXPORT_URL}?"
        f"{urlencode(params)}"
    )


def request_3dep_export(
    bounds: GeographicBoundingBox,
    width_px: int,
    height_px: int,
    timeout_seconds: float = 30.0,
) -> DemExportResult:
    """Request 3DEP export metadata."""

    url = build_3dep_export_url(
        bounds=bounds,
        width_px=width_px,
        height_px=height_px,
    )

    transport = httpx.HTTPTransport(
        local_address="0.0.0.0",
        retries=2,
    )

    try:
        with httpx.Client(
            transport=transport,
            timeout=timeout_seconds,
            headers={
                "User-Agent": (
                    "GeoVaris-Coverage-Intelligence/0.1"
                ),
            },
        ) as client:
            response = client.get(url)

            if response.is_error:
                body = response.text.strip()

                raise RuntimeError(
                    "USGS 3DEP export metadata request failed. "
                    f"HTTP {response.status_code}. "
                    f"Response: {body[:2000]!r}"
                )

            payload = response.json()

    except httpx.HTTPError as exc:
        raise RuntimeError(
            "USGS 3DEP export metadata network request failed: "
            f"{exc}"
        ) from exc

    href = payload.get("href")
    width = payload.get("width")
    height = payload.get("height")
    extent = payload.get("extent")

    if not isinstance(href, str) or not href:
        raise RuntimeError(
            "USGS 3DEP export response did not contain "
            f"a valid href: {payload}"
        )

    if not isinstance(width, int) or width <= 0:
        raise RuntimeError(
            "USGS 3DEP export response contained "
            f"an invalid width: {width!r}"
        )

    if not isinstance(height, int) or height <= 0:
        raise RuntimeError(
            "USGS 3DEP export response contained "
            f"an invalid height: {height!r}"
        )

    if not isinstance(extent, dict):
        raise RuntimeError(
            "USGS 3DEP export response contained "
            f"an invalid extent: {extent!r}"
        )

    return DemExportResult(
        href=href,
        width=width,
        height=height,
        extent=extent,
    )


def _stream_3dep_raster(
    params: dict[str, str],
    destination_path: str,
    max_size_bytes: int,
    timeout_seconds: float,
) -> DemDownloadResult:
    """Stream one USGS 3DEP GeoTIFF to disk."""

    if max_size_bytes <= 0:
        raise ValueError(
            "max_size_bytes must be greater than zero; "
            f"got {max_size_bytes}."
        )

    destination = Path(
        destination_path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    transport = httpx.HTTPTransport(
        local_address="0.0.0.0",
        retries=2,
    )

    bytes_written = 0

    try:
        with httpx.Client(
            transport=transport,
            timeout=timeout_seconds,
            headers={
                "User-Agent": (
                    "GeoVaris-Coverage-Intelligence/0.1"
                ),
            },
        ) as client:
            with client.stream(
                "GET",
                USGS_3DEP_EXPORT_URL,
                params=params,
            ) as response:

                if response.is_error:
                    error_bytes = response.read()

                    error_text = error_bytes.decode(
                        response.encoding or "utf-8",
                        errors="replace",
                    ).strip()

                    raise RuntimeError(
                        "USGS 3DEP raster export failed. "
                        f"HTTP {response.status_code}. "
                        f"URL: {response.request.url}. "
                        f"Response: {error_text[:2000]!r}"
                    )

                content_type = response.headers.get(
                    "content-type",
                    "",
                ).lower()

                if (
                    "tiff" not in content_type
                    and "octet-stream" not in content_type
                ):
                    unexpected_bytes = response.read()

                    unexpected_text = unexpected_bytes.decode(
                        response.encoding or "utf-8",
                        errors="replace",
                    ).strip()

                    raise RuntimeError(
                        "USGS 3DEP export did not return a TIFF. "
                        f"Content-Type: {content_type!r}. "
                        f"Response: {unexpected_text[:2000]!r}"
                    )

                content_length = response.headers.get(
                    "content-length"
                )

                if content_length is not None:
                    try:
                        expected_size = int(
                            content_length
                        )
                    except ValueError as exc:
                        raise RuntimeError(
                            "USGS 3DEP returned an invalid "
                            "Content-Length header: "
                            f"{content_length!r}"
                        ) from exc

                    if expected_size > max_size_bytes:
                        raise RuntimeError(
                            "USGS 3DEP raster exceeds configured "
                            "size limit: "
                            f"{expected_size} bytes > "
                            f"{max_size_bytes} bytes."
                        )

                with destination.open(
                    "wb"
                ) as output_file:
                    for chunk in response.iter_bytes():
                        bytes_written += len(chunk)

                        if bytes_written > max_size_bytes:
                            raise RuntimeError(
                                "USGS 3DEP raster exceeded "
                                "configured size limit while "
                                "downloading: "
                                f"{max_size_bytes} bytes."
                            )

                        output_file.write(chunk)

    except Exception:
        if destination.exists():
            destination.unlink()

        raise

    return DemDownloadResult(
        file_path=str(destination),
        size_bytes=bytes_written,
        source_href=USGS_3DEP_EXPORT_URL,
    )


def download_3dep_raster(
    bounds: GeographicBoundingBox,
    width_px: int,
    height_px: int,
    destination_path: str,
    max_size_bytes: int = 50_000_000,
    timeout_seconds: float = 60.0,
) -> DemDownloadResult:
    """Download 3DEP using geographic WGS84 bounds."""

    params = _build_3dep_export_params(
        bounds=bounds,
        width_px=width_px,
        height_px=height_px,
        response_format="image",
    )

    return _stream_3dep_raster(
        params=params,
        destination_path=destination_path,
        max_size_bytes=max_size_bytes,
        timeout_seconds=timeout_seconds,
    )


def inspect_dem_raster(
    file_path: str,
) -> DemRasterInfo:
    """Inspect and validate a local DEM raster."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"DEM raster does not exist: {file_path}"
        )

    with rasterio.open(path) as dataset:
        if dataset.count < 1:
            raise RuntimeError(
                f"DEM raster contains no bands: {file_path}"
            )

        if dataset.crs is None:
            raise RuntimeError(
                f"DEM raster has no CRS: {file_path}"
            )

        elevation = dataset.read(
            1,
            masked=True,
        )

        if elevation.count() == 0:
            raise RuntimeError(
                "DEM raster contains no valid elevation cells: "
                f"{file_path}"
            )

        return DemRasterInfo(
            file_path=str(path),
            crs=str(dataset.crs),
            width=dataset.width,
            height=dataset.height,
            pixel_size_x=float(
                dataset.res[0]
            ),
            pixel_size_y=float(
                dataset.res[1]
            ),
            data_type=str(
                dataset.dtypes[0]
            ),
            nodata=(
                float(dataset.nodata)
                if dataset.nodata is not None
                else None
            ),
            min_elevation_m=float(
                elevation.min()
            ),
            max_elevation_m=float(
                elevation.max()
            ),
            mean_elevation_m=float(
                elevation.mean()
            ),
        )


def calculate_utm_epsg(
    latitude: float,
    longitude: float,
) -> int:
    """Return WGS84 UTM EPSG code for a coordinate."""

    validate_coordinate(
        latitude,
        longitude,
    )

    if latitude < -80.0 or latitude > 84.0:
        raise ValueError(
            "UTM terrain grids currently support latitudes "
            "from -80 through 84 degrees; "
            f"got {latitude}."
        )

    zone = int(
        (longitude + 180.0) // 6.0
    ) + 1

    zone = max(
        1,
        min(zone, 60),
    )

    if latitude >= 0:
        return 32600 + zone

    return 32700 + zone


def plan_terrain_grid(
    latitude: float,
    longitude: float,
    radius_m: float,
    resolution_m: float,
) -> TerrainGridPlan:
    """Plan an exact-resolution square RF terrain grid."""

    validate_coordinate(
        latitude,
        longitude,
    )

    validate_radius(radius_m)

    if resolution_m <= 0:
        raise ValueError(
            "resolution_m must be greater than zero; "
            f"got {resolution_m}."
        )

    epsg = calculate_utm_epsg(
        latitude=latitude,
        longitude=longitude,
    )

    target_crs = f"EPSG:{epsg}"

    transformer = Transformer.from_crs(
        "EPSG:4326",
        target_crs,
        always_xy=True,
    )

    center_x_m, center_y_m = transformer.transform(
        longitude,
        latitude,
    )

    requested_size_m = (
        radius_m * 2.0
    )

    width_px = math.ceil(
        requested_size_m / resolution_m
    )

    height_px = math.ceil(
        requested_size_m / resolution_m
    )

    actual_width_m = (
        width_px * resolution_m
    )

    actual_height_m = (
        height_px * resolution_m
    )

    west_m = (
        center_x_m
        - actual_width_m / 2.0
    )

    east_m = (
        center_x_m
        + actual_width_m / 2.0
    )

    south_m = (
        center_y_m
        - actual_height_m / 2.0
    )

    north_m = (
        center_y_m
        + actual_height_m / 2.0
    )

    return TerrainGridPlan(
        target_crs=target_crs,
        center_x_m=center_x_m,
        center_y_m=center_y_m,
        west_m=west_m,
        south_m=south_m,
        east_m=east_m,
        north_m=north_m,
        resolution_m=resolution_m,
        width_px=width_px,
        height_px=height_px,
    )


def _split_pixel_count(
    total_pixels: int,
    parts: int,
) -> list[int]:
    """Split pixels across parts without losing any cells."""

    if parts <= 0:
        raise ValueError(
            f"parts must be greater than zero; got {parts}."
        )

    if parts > total_pixels:
        raise ValueError(
            "Cannot create more tile divisions than pixels; "
            f"pixels={total_pixels}, parts={parts}."
        )

    base = total_pixels // parts
    remainder = total_pixels % parts

    return [
        base + (1 if index < remainder else 0)
        for index in range(parts)
    ]


def plan_dem_tiles(
    grid: TerrainGridPlan,
    rows: int = 2,
    columns: int = 2,
) -> list[DemTilePlan]:
    """Split an RF terrain grid into aligned rectangular tiles.

    Rows are ordered north to south.
    Columns are ordered west to east.

    Tile dimensions always sum exactly to the original grid.
    """

    if rows <= 0:
        raise ValueError(
            f"rows must be greater than zero; got {rows}."
        )

    if columns <= 0:
        raise ValueError(
            "columns must be greater than zero; "
            f"got {columns}."
        )

    row_heights = _split_pixel_count(
        grid.height_px,
        rows,
    )

    column_widths = _split_pixel_count(
        grid.width_px,
        columns,
    )

    tiles: list[DemTilePlan] = []

    row_start_px = 0

    for row_index, tile_height_px in enumerate(
        row_heights
    ):
        tile_north_m = (
            grid.north_m
            - row_start_px
            * grid.resolution_m
        )

        tile_south_m = (
            tile_north_m
            - tile_height_px
            * grid.resolution_m
        )

        column_start_px = 0

        for (
            column_index,
            tile_width_px,
        ) in enumerate(column_widths):

            tile_west_m = (
                grid.west_m
                + column_start_px
                * grid.resolution_m
            )

            tile_east_m = (
                tile_west_m
                + tile_width_px
                * grid.resolution_m
            )

            tiles.append(
                DemTilePlan(
                    row=row_index,
                    column=column_index,
                    target_crs=grid.target_crs,
                    west_m=tile_west_m,
                    south_m=tile_south_m,
                    east_m=tile_east_m,
                    north_m=tile_north_m,
                    resolution_m=grid.resolution_m,
                    width_px=tile_width_px,
                    height_px=tile_height_px,
                )
            )

            column_start_px += (
                tile_width_px
            )

        row_start_px += (
            tile_height_px
        )

    return tiles


def download_3dep_for_grid(
    grid: TerrainGridPlan,
    destination_path: str,
    max_size_bytes: int = 100_000_000,
    timeout_seconds: float = 120.0,
) -> DemDownloadResult:
    """Attempt one direct 3DEP export for a complete grid."""

    params = _build_3dep_grid_export_params(
        grid=grid,
        response_format="image",
    )

    return _stream_3dep_raster(
        params=params,
        destination_path=destination_path,
        max_size_bytes=max_size_bytes,
        timeout_seconds=timeout_seconds,
    )


def download_3dep_tile(
    tile: DemTilePlan,
    destination_path: str,
    max_size_bytes: int = 50_000_000,
    timeout_seconds: float = 120.0,
) -> DemDownloadResult:
    """Download one planned terrain tile from 3DEP."""

    params = _build_3dep_tile_export_params(
        tile=tile,
        response_format="image",
    )

    return _stream_3dep_raster(
        params=params,
        destination_path=destination_path,
        max_size_bytes=max_size_bytes,
        timeout_seconds=timeout_seconds,
    )


def mosaic_dem_tiles(
    grid: TerrainGridPlan,
    tile_files: dict[tuple[int, int], str],
    destination_path: str,
) -> DemMosaicResult:
    """Mosaic aligned DEM tiles into one RF terrain raster.

    tile_files keys are (row, column).

    Every tile is validated for:
    - file existence
    - CRS
    - pixel resolution
    - expected dimensions
    - expected spatial transform

    Missing or invalid tiles cause the mosaic operation to fail.
    """

    expected_tiles = plan_dem_tiles(
        grid,
        rows=2,
        columns=2,
    )

    expected_keys = {
        (tile.row, tile.column)
        for tile in expected_tiles
    }

    supplied_keys = set(
        tile_files.keys()
    )

    if supplied_keys != expected_keys:
        missing = sorted(
            expected_keys - supplied_keys
        )

        extra = sorted(
            supplied_keys - expected_keys
        )

        raise ValueError(
            "Tile file mapping does not match expected 2x2 grid. "
            f"Missing={missing}, extra={extra}."
        )

    destination = Path(
        destination_path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mosaic = np.full(
        (
            grid.height_px,
            grid.width_px,
        ),
        DEFAULT_DEM_NODATA,
        dtype=np.float32,
    )

    row_offsets: dict[int, int] = {}
    column_offsets: dict[int, int] = {}

    current_row_offset = 0

    for row in sorted(
        {
            tile.row
            for tile in expected_tiles
        }
    ):
        row_offsets[row] = current_row_offset

        row_height = next(
            tile.height_px
            for tile in expected_tiles
            if tile.row == row
        )

        current_row_offset += (
            row_height
        )

    current_column_offset = 0

    for column in sorted(
        {
            tile.column
            for tile in expected_tiles
        }
    ):
        column_offsets[column] = (
            current_column_offset
        )

        column_width = next(
            tile.width_px
            for tile in expected_tiles
            if tile.column == column
        )

        current_column_offset += (
            column_width
        )

    for tile in expected_tiles:
        key = (
            tile.row,
            tile.column,
        )

        source_path = Path(
            tile_files[key]
        )

        if not source_path.exists():
            raise FileNotFoundError(
                "DEM tile does not exist for "
                f"row={tile.row}, column={tile.column}: "
                f"{source_path}"
            )

        expected_transform = from_origin(
            tile.west_m,
            tile.north_m,
            tile.resolution_m,
            tile.resolution_m,
        )

        with rasterio.open(
            source_path
        ) as src:
            if src.crs is None:
                raise RuntimeError(
                    f"DEM tile has no CRS: {source_path}"
                )

            if str(src.crs) != tile.target_crs:
                raise RuntimeError(
                    "DEM tile CRS mismatch. "
                    f"Expected {tile.target_crs}, "
                    f"got {src.crs}: {source_path}"
                )

            if src.width != tile.width_px:
                raise RuntimeError(
                    "DEM tile width mismatch. "
                    f"Expected {tile.width_px}, "
                    f"got {src.width}: {source_path}"
                )

            if src.height != tile.height_px:
                raise RuntimeError(
                    "DEM tile height mismatch. "
                    f"Expected {tile.height_px}, "
                    f"got {src.height}: {source_path}"
                )

            if not math.isclose(
                float(src.res[0]),
                tile.resolution_m,
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    "DEM tile X resolution mismatch. "
                    f"Expected {tile.resolution_m}, "
                    f"got {src.res[0]}: {source_path}"
                )

            if not math.isclose(
                float(src.res[1]),
                tile.resolution_m,
                rel_tol=0.0,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    "DEM tile Y resolution mismatch. "
                    f"Expected {tile.resolution_m}, "
                    f"got {src.res[1]}: {source_path}"
                )

            for actual, expected in zip(
                src.transform,
                expected_transform,
            ):
                if not math.isclose(
                    float(actual),
                    float(expected),
                    rel_tol=0.0,
                    abs_tol=1e-6,
                ):
                    raise RuntimeError(
                        "DEM tile transform does not match "
                        "the planned terrain grid: "
                        f"{source_path}"
                    )

            data = src.read(
                1,
                masked=True,
            )

            filled = data.filled(
                DEFAULT_DEM_NODATA
            ).astype(
                np.float32
            )

        row_offset = row_offsets[
            tile.row
        ]

        column_offset = column_offsets[
            tile.column
        ]

        row_end = (
            row_offset
            + tile.height_px
        )

        column_end = (
            column_offset
            + tile.width_px
        )

        mosaic[
            row_offset:row_end,
            column_offset:column_end,
        ] = filled

    destination_transform = from_origin(
        grid.west_m,
        grid.north_m,
        grid.resolution_m,
        grid.resolution_m,
    )

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "crs": grid.target_crs,
        "transform": destination_transform,
        "width": grid.width_px,
        "height": grid.height_px,
        "nodata": DEFAULT_DEM_NODATA,
        "compress": "deflate",
    }

    try:
        with rasterio.open(
            destination,
            "w",
            **profile,
        ) as dst:
            dst.write(
                mosaic,
                1,
            )

    except Exception:
        if destination.exists():
            destination.unlink()

        raise

    return DemMosaicResult(
        destination_path=str(destination),
        target_crs=grid.target_crs,
        resolution_m=grid.resolution_m,
        width_px=grid.width_px,
        height_px=grid.height_px,
        tile_count=len(expected_tiles),
        nodata=DEFAULT_DEM_NODATA,
    )


def reproject_dem_to_grid(
    source_path: str,
    destination_path: str,
    grid: TerrainGridPlan,
) -> DemReprojectionResult:
    """Reproject a DEM into the planned RF terrain grid."""

    source = Path(
        source_path
    )

    if not source.exists():
        raise FileNotFoundError(
            f"Source DEM does not exist: {source_path}"
        )

    destination = Path(
        destination_path
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination_transform = from_origin(
        grid.west_m,
        grid.north_m,
        grid.resolution_m,
        grid.resolution_m,
    )

    source_crs = ""

    try:
        with rasterio.open(
            source
        ) as src:
            if src.crs is None:
                raise RuntimeError(
                    f"Source DEM has no CRS: {source_path}"
                )

            source_crs = str(
                src.crs
            )

            profile = src.profile.copy()

            profile.update(
                driver="GTiff",
                dtype="float32",
                count=1,
                crs=grid.target_crs,
                transform=destination_transform,
                width=grid.width_px,
                height=grid.height_px,
                nodata=DEFAULT_DEM_NODATA,
                compress="deflate",
            )

            with rasterio.open(
                destination,
                "w",
                **profile,
            ) as dst:
                reproject(
                    source=rasterio.band(
                        src,
                        1,
                    ),
                    destination=rasterio.band(
                        dst,
                        1,
                    ),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    src_nodata=src.nodata,
                    dst_transform=destination_transform,
                    dst_crs=grid.target_crs,
                    dst_nodata=DEFAULT_DEM_NODATA,
                    resampling=Resampling.bilinear,
                )

    except Exception:
        if destination.exists():
            destination.unlink()

        raise

    return DemReprojectionResult(
        source_path=str(source),
        destination_path=str(destination),
        source_crs=source_crs,
        target_crs=grid.target_crs,
        resolution_m=grid.resolution_m,
        width_px=grid.width_px,
        height_px=grid.height_px,
        resampling_method="bilinear",
    )