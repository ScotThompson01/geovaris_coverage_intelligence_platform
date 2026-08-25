-- GeoVaris Coverage Intelligence
-- Migration 004: Snapshot DEM lineage into coverage runs

ALTER TABLE coverage_runs
    ADD COLUMN IF NOT EXISTS site_ground_elevation_m DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS dem_source TEXT,
    ADD COLUMN IF NOT EXISTS dem_version TEXT,
    ADD COLUMN IF NOT EXISTS dem_horizontal_crs TEXT,
    ADD COLUMN IF NOT EXISTS dem_vertical_datum TEXT,
    ADD COLUMN IF NOT EXISTS dem_units TEXT,
    ADD COLUMN IF NOT EXISTS dem_resolution_m DOUBLE PRECISION;

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_dem_resolution_nonnegative
    CHECK (
        dem_resolution_m IS NULL
        OR dem_resolution_m >= 0
    );