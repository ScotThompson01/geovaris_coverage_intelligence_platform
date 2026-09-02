-- GeoVaris Coverage Intelligence
-- Migration 010: Add governed FCC Fabric location analytics
--
-- Stores governed Broadband Serviceable Location Fabric point data
-- and the lineage required to reproduce Fabric-location coverage
-- analytics.
--
-- IMPORTANT:
-- FCC Fabric data may be subject to licensing, contractual,
-- confidentiality, security, and redistribution restrictions.
-- This schema does not imply that Fabric data may be publicly
-- exported or redistributed.
--
-- The MVP calculation treats each governed Fabric location as a
-- point and counts locations whose point geometry intersects the
-- stored coverage geometry.
--
-- Because the RF footprint itself is an engineering estimate,
-- covered_fabric_locations represents estimated Fabric locations
-- covered, not guaranteed service availability.
--
-- Multiple governed Fabric releases may coexist in this table.
-- The same location_id may therefore appear in more than one
-- dataset source/version combination.

CREATE TABLE IF NOT EXISTS fabric_locations (
    location_id TEXT NOT NULL,

    state_fips TEXT,
    county_fips TEXT,

    dataset_source TEXT NOT NULL,
    fabric_version TEXT NOT NULL,
    dataset_vintage TEXT,

    geometry geometry(Point, 4326) NOT NULL,

    imported_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fabric_locations_pk
        PRIMARY KEY (
            dataset_source,
            fabric_version,
            location_id
        ),

    CONSTRAINT fabric_locations_location_id_not_blank
        CHECK (
            btrim(location_id) <> ''
        ),

    CONSTRAINT fabric_locations_dataset_source_not_blank
        CHECK (
            btrim(dataset_source) <> ''
        ),

    CONSTRAINT fabric_locations_fabric_version_not_blank
        CHECK (
            btrim(fabric_version) <> ''
        )
);

CREATE INDEX IF NOT EXISTS fabric_locations_geometry_gix
    ON fabric_locations
    USING GIST (geometry);

CREATE INDEX IF NOT EXISTS fabric_locations_state_county_idx
    ON fabric_locations (
        state_fips,
        county_fips
    );

CREATE INDEX IF NOT EXISTS fabric_locations_dataset_idx
    ON fabric_locations (
        dataset_source,
        fabric_version,
        dataset_vintage
    );

ALTER TABLE coverage_runs
    ADD COLUMN IF NOT EXISTS fabric_dataset_source TEXT,
    ADD COLUMN IF NOT EXISTS fabric_dataset_vintage TEXT,
    ADD COLUMN IF NOT EXISTS fabric_geometry_basis TEXT,
    ADD COLUMN IF NOT EXISTS fabric_calculated_at TIMESTAMPTZ;

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_covered_fabric_locations_nonnegative
    CHECK (
        covered_fabric_locations IS NULL
        OR covered_fabric_locations >= 0
    );

CREATE INDEX IF NOT EXISTS idx_coverage_runs_fabric_calculated_at
    ON coverage_runs (
        fabric_calculated_at
    )
    WHERE fabric_calculated_at IS NOT NULL;

COMMENT ON TABLE fabric_locations IS
    'Governed FCC Broadband Serviceable Location Fabric point data used for GeoVaris Fabric-location coverage analytics. Multiple governed releases may coexist. Access and redistribution remain subject to applicable licensing and contractual restrictions.';

COMMENT ON COLUMN fabric_locations.location_id IS
    'Governed unique identifier for the Broadband Serviceable Location record within the associated dataset source and Fabric version.';

COMMENT ON COLUMN fabric_locations.state_fips IS
    'Optional state FIPS code associated with the governed Fabric location.';

COMMENT ON COLUMN fabric_locations.county_fips IS
    'Optional county FIPS code associated with the governed Fabric location.';

COMMENT ON COLUMN fabric_locations.dataset_source IS
    'Authoritative source organization and dataset family for this governed Fabric record.';

COMMENT ON COLUMN fabric_locations.fabric_version IS
    'Exact governed FCC Fabric release/version associated with this location.';

COMMENT ON COLUMN fabric_locations.dataset_vintage IS
    'Optional governed dataset vintage or effective-period identifier.';

COMMENT ON COLUMN fabric_locations.geometry IS
    'Broadband Serviceable Location point stored as EPSG:4326 geometry.';

COMMENT ON COLUMN coverage_runs.covered_fabric_locations IS
    'Estimated number of governed Fabric locations intersecting this coverage run footprint. This is not a guarantee of actual service availability.';

COMMENT ON COLUMN coverage_runs.fabric_version IS
    'Exact governed FCC Fabric release/version used for this coverage run Fabric analysis.';

COMMENT ON COLUMN coverage_runs.fabric_dataset_source IS
    'Authoritative source organization and Fabric dataset family used for this coverage run.';

COMMENT ON COLUMN coverage_runs.fabric_dataset_vintage IS
    'Governed Fabric dataset vintage or effective-period identifier used for this coverage run.';

COMMENT ON COLUMN coverage_runs.fabric_geometry_basis IS
    'Coverage representation used for the Fabric-location calculation, such as display_geometry or authoritative_raster.';

COMMENT ON COLUMN coverage_runs.fabric_calculated_at IS
    'Timestamp when Fabric-location analytics were calculated for this coverage run.';
