$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "GeoVaris Coverage Intelligence"
Write-Host "Starting RF development worker..."
Write-Host ""

# ------------------------------------------------------------
# Resolve repository paths.
# ------------------------------------------------------------

$repoRoot = Resolve-Path (
    Join-Path $PSScriptRoot "..\.."
)

$rfEngineRoot = Join-Path `
    $repoRoot `
    "rf-engine"

$rfSourcePath = Join-Path `
    $rfEngineRoot `
    "src"

$webEnvPath = Join-Path `
    $repoRoot `
    "geovaris-coverage-intelligence\.env.local"

$demPath = Join-Path `
    $rfEngineRoot `
    "data\dem\test002_60km_30m_utm17.tif"

$clutterPath = Join-Path `
    $rfEngineRoot `
    "data\clutter\Annual_NLCD_LndCov_2025_CU_C1V2_930a08f4-02fc-4bb2-abe7-97b78b84b4c5.tiff"

$coverageOutputPath = Join-Path `
    $rfEngineRoot `
    "data\coverage"

# ------------------------------------------------------------
# Load the local development database URL without displaying it.
# ------------------------------------------------------------

if (-not (Test-Path $webEnvPath)) {
    throw (
        "GeoVaris web environment file was not found: " +
        $webEnvPath
    )
}

$databaseUrlLine = Get-Content $webEnvPath |
    Where-Object {
        $_ -match '^\s*DATABASE_URL='
    } |
    Select-Object -First 1

if (-not $databaseUrlLine) {
    throw (
        "DATABASE_URL was not found in " +
        $webEnvPath
    )
}

$databaseUrl = (
    $databaseUrlLine `
        -replace '^\s*DATABASE_URL=', ''
).Trim()

# Support quoted .env values.
if (
    ($databaseUrl.StartsWith('"') -and
     $databaseUrl.EndsWith('"')) -or
    ($databaseUrl.StartsWith("'") -and
     $databaseUrl.EndsWith("'"))
) {
    $databaseUrl = $databaseUrl.Substring(
        1,
        $databaseUrl.Length - 2
    )
}

if (-not $databaseUrl) {
    throw "DATABASE_URL is empty."
}

$env:GEOVARIS_DATABASE_URL = $databaseUrl

# ------------------------------------------------------------
# Configure Python and Rapid Coverage development datasets.
# ------------------------------------------------------------

$env:GEOVARIS_RAPID_DEM_RASTER_PATH = `
    $demPath

$env:GEOVARIS_ITM_DEM_RASTER_PATH = `
    $demPath

$env:GEOVARIS_CLUTTER_RASTER_PATH = `
    $clutterPath

$env:GEOVARIS_COVERAGE_OUTPUT_DIR = `
    $coverageOutputPath

# ------------------------------------------------------------
# Validate governed local development datasets.
# ------------------------------------------------------------

if (
    -not (
        Test-Path `
            $env:GEOVARIS_RAPID_DEM_RASTER_PATH
    )
) {
    throw (
        "Rapid Coverage DEM was not found: " +
        $env:GEOVARIS_RAPID_DEM_RASTER_PATH
    )
}

if (
    -not (
        Test-Path `
            $env:GEOVARIS_CLUTTER_RASTER_PATH
    )
) {
    throw (
        "Rapid Coverage clutter raster was not found: " +
        $env:GEOVARIS_CLUTTER_RASTER_PATH
    )
}

if (
    -not (
        Test-Path `
            $env:GEOVARIS_COVERAGE_OUTPUT_DIR
    )
) {
    New-Item `
        -ItemType Directory `
        -Path $env:GEOVARIS_COVERAGE_OUTPUT_DIR `
        -Force |
        Out-Null
}

# ------------------------------------------------------------
# Locate GDAL viewshed.
#
# Prefer an explicitly configured value. Otherwise locate the
# executable from an installed QGIS distribution.
# ------------------------------------------------------------

$gdalViewshedPath = `
    $env:GEOVARIS_GDAL_VIEWSHED_PATH

if (
    $gdalViewshedPath -and
    -not (Test-Path $gdalViewshedPath)
) {
    $gdalViewshedPath = $null
}

if (-not $gdalViewshedPath) {
    $knownQgisPath = `
        "C:\Program Files\QGIS 4.0.3\bin\gdal_viewshed.exe"

    if (Test-Path $knownQgisPath) {
        $gdalViewshedPath = $knownQgisPath
    }
}

if (-not $gdalViewshedPath) {
    $gdalCandidate = Get-ChildItem `
        "C:\Program Files" `
        -Recurse `
        -Filter "gdal_viewshed.exe" `
        -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($gdalCandidate) {
        $gdalViewshedPath = `
            $gdalCandidate.FullName
    }
}

if (-not $gdalViewshedPath) {
    throw @"
GDAL viewshed executable was not found.

Install QGIS/GDAL or configure:

GEOVARIS_GDAL_VIEWSHED_PATH

with the full path to gdal_viewshed.exe.
"@
}

$env:GEOVARIS_GDAL_VIEWSHED_PATH = `
    $gdalViewshedPath

# ------------------------------------------------------------
# A continuous worker must not remain pinned to a prior
# development/test coverage run.
# ------------------------------------------------------------

Remove-Item `
    Env:GEOVARIS_COVERAGE_RUN_ID `
    -ErrorAction SilentlyContinue

# ------------------------------------------------------------
# Startup summary.
#
# Do not display database credentials.
# ------------------------------------------------------------

Write-Host "Configuration validated."
Write-Host ""
Write-Host "DEM:"
Write-Host "  $env:GEOVARIS_RAPID_DEM_RASTER_PATH"
Write-Host ""
Write-Host "ITM DEM:"
Write-Host "  $env:GEOVARIS_ITM_DEM_RASTER_PATH"
Write-Host ""
Write-Host "Clutter:"
Write-Host "  $env:GEOVARIS_CLUTTER_RASTER_PATH"
Write-Host ""
Write-Host "GDAL viewshed:"
Write-Host "  $env:GEOVARIS_GDAL_VIEWSHED_PATH"
Write-Host ""
Write-Host "Coverage output:"
Write-Host "  $env:GEOVARIS_COVERAGE_OUTPUT_DIR"
Write-Host ""
Write-Host "Database:"
Write-Host "  Configured from local .env.local"
Write-Host ""
Write-Host "Press Ctrl+C to stop the worker."
Write-Host ""

# ------------------------------------------------------------
# Start the continuous GeoVaris RF development worker.
# ------------------------------------------------------------

Push-Location $repoRoot

try {
    python -m geovaris_rf.worker_loop

    if ($LASTEXITCODE -ne 0) {
        throw (
            "GeoVaris RF worker exited with code " +
            $LASTEXITCODE
        )
    }
}
finally {
    Pop-Location
}