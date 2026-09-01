-- GeoVaris Coverage Intelligence
-- Migration 008: Add governed Census population blocks
--
-- Stores Census block geography and population counts used for
-- population-covered analytics.
--
-- The table is designed for spatially limited loading. GeoVaris does not
-- need to load national-scale data when only selected states/counties are
-- required.
--
-- Geometry is stored in EPSG:4326 for interoperability with coverage
-- geometry. Area-based calculations should cast/project appropriately and
-- must not use raw longitude/latitude degrees as area units.
--
-- Population calculations are engineering/business analytics estimates.
-- Partial-block coverage will initially use an area-weighted allocation
-- method and should be labeled accordingly.

CREATE TABLE IF NOT EXISTS population_blocks (
    geoid TEXT PRIMARY KEY,

    state_fips TEXT NOT NULL,
    county_fips TEXT NOT NULL,
    tract_code TEXT NOT NULL,
    block_code TEXT NOT NULL,

    population INTEGER NOT NULL,
    housing_units INTEGER,

    land_area_sq_m DOUBLE PRECISION,
    water_area_sq_m DOUBLE PRECISION,

    dataset_source TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    dataset_vintage INTEGER NOT NULL,

    geometry geometry(MultiPolygon, 4326) NOT NULL,

    imported_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT population_blocks_population_nonnegative
        CHECK (
            population >= 0
        ),

    CONSTRAINT population_blocks_housing_units_nonnegative
        CHECK (
            housing_units IS NULL
            OR housing_units >= 0
        ),

    CONSTRAINT population_blocks_land_area_nonnegative
        CHECK (
            land_area_sq_m IS NULL
            OR land_area_sq_m >= 0
        ),

    CONSTRAINT population_blocks_water_area_nonnegative
        CHECK (
            water_area_sq_m IS NULL
            OR water_area_sq_m >= 0
        ),

    CONSTRAINT population_blocks_dataset_vintage_valid
        CHECK (
            dataset_vintage >= 2000
            AND dataset_vintage <= 2100
        )
);

CREATE INDEX IF NOT EXISTS population_blocks_geometry_gix
    ON population_blocks
    USING GIST (geometry);

CREATE INDEX IF NOT EXISTS population_blocks_state_county_idx
    ON population_blocks (
        state_fips,
        county_fips
    );

CREATE INDEX IF NOT EXISTS population_blocks_dataset_idx
    ON population_blocks (
        dataset_source,
        dataset_version,
        dataset_vintage
    );

COMMENT ON TABLE population_blocks IS
    'Governed Census block geography and population data used for GeoVaris population-covered analytics.';

COMMENT ON COLUMN population_blocks.geoid IS
    'Unique Census block GEOID.';

COMMENT ON COLUMN population_blocks.population IS
    'Official population count associated with the Census block.';

COMMENT ON COLUMN population_blocks.geometry IS
    'Census block boundary stored as EPSG:4326 MultiPolygon geometry.';

COMMENT ON COLUMN population_blocks.dataset_source IS
    'Authoritative source organization and dataset family.';

COMMENT ON COLUMN population_blocks.dataset_version IS
    'Exact governed dataset release/version used for reproducibility.';

COMMENT ON COLUMN population_blocks.dataset_vintage IS
    'Census vintage year associated with the block geography and population data.';