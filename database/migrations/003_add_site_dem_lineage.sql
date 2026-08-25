-- GeoVaris Coverage Intelligence
-- Migration 003: Add governed DEM lineage fields to sites

ALTER TABLE sites
    ADD COLUMN IF NOT EXISTS ground_elevation_source TEXT,
    ADD COLUMN IF NOT EXISTS ground_elevation_version TEXT,
    ADD COLUMN IF NOT EXISTS ground_elevation_horizontal_crs TEXT,
    ADD COLUMN IF NOT EXISTS ground_elevation_vertical_datum TEXT,
    ADD COLUMN IF NOT EXISTS ground_elevation_units TEXT,
    ADD COLUMN IF NOT EXISTS ground_elevation_resolution_m DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS ground_elevation_updated_at TIMESTAMPTZ;

ALTER TABLE sites
    ADD CONSTRAINT sites_ground_elevation_resolution_nonnegative
    CHECK (
        ground_elevation_resolution_m IS NULL
        OR ground_elevation_resolution_m >= 0
    );