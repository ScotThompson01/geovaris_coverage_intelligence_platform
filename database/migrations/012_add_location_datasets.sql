-- GeoVaris Coverage Intelligence
-- Migration 012
--
-- Governed point-location datasets for FCC Fabric,
-- mock Fabric, customer-provided location data, and
-- other future point-based coverage analytics.
--
-- Important:
--   Dataset ownership is customer-scoped.
--   Source CSV column names are stored as metadata
--   rather than hard-coded into the point schema.

CREATE TABLE location_datasets (
    id UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    customer_id UUID NOT NULL
        REFERENCES customers(id)
        ON DELETE CASCADE,

    name TEXT NOT NULL,

    dataset_type TEXT NOT NULL
        CHECK (
            dataset_type IN (
                'mock_fcc_fabric',
                'fcc_fabric',
                'customer_locations',
                'other'
            )
        ),

    source_name TEXT NOT NULL,

    source_version TEXT,

    effective_date DATE,

    acquisition_date DATE,

    crs_epsg INTEGER NOT NULL
        DEFAULT 4326,

    is_mock BOOLEAN NOT NULL
        DEFAULT FALSE,

    original_filename TEXT,

    source_file_sha256 TEXT,

    /*
     * Flexible source-column mapping.
     *
     * Example:
     *
     * {
     *   "location_id": "location_id",
     *   "latitude": "latitude",
     *   "longitude": "longitude"
     * }
     *
     * Future CSV files may use completely different
     * source column names without changing the
     * normalized database schema.
     */
    column_mapping JSONB NOT NULL
        DEFAULT '{}'::jsonb,

    /*
     * Optional dataset-specific metadata such as:
     *
     * release identifiers
     * licensing notes
     * geographic description
     * processing assumptions
     * source documentation
     */
    metadata JSONB NOT NULL
        DEFAULT '{}'::jsonb,

    quality_status TEXT NOT NULL
        DEFAULT 'unverified'
        CHECK (
            quality_status IN (
                'unverified',
                'validated',
                'approved',
                'rejected'
            )
        ),

    import_status TEXT NOT NULL
        DEFAULT 'registered'
        CHECK (
            import_status IN (
                'registered',
                'importing',
                'ready',
                'failed'
            )
        ),

    row_count INTEGER,

    imported_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    CHECK (
        row_count IS NULL
        OR row_count >= 0
    )
);

CREATE INDEX location_datasets_customer_id_idx
    ON location_datasets(customer_id);

CREATE INDEX location_datasets_customer_type_idx
    ON location_datasets(
        customer_id,
        dataset_type
    );


CREATE TABLE location_dataset_points (
    id BIGSERIAL PRIMARY KEY,

    dataset_id UUID NOT NULL
        REFERENCES location_datasets(id)
        ON DELETE CASCADE,

    source_location_id TEXT NOT NULL,

    latitude DOUBLE PRECISION NOT NULL,

    longitude DOUBLE PRECISION NOT NULL,

    /*
     * Normalized spatial representation used for
     * PostGIS point-in-polygon analysis.
     *
     * Source coordinates are validated and converted
     * to EPSG:4326 before insertion.
     */
    location geometry(Point, 4326) NOT NULL,

    /*
     * Preserve optional source attributes without
     * requiring schema changes for every Fabric or
     * customer location file.
     *
     * Example:
     *
     * {
     *   "unit_count": "4",
     *   "bsl_flag": "1",
     *   "county_geoid": "12095",
     *   "fcc_rel": "06302026"
     * }
     */
    source_attributes JSONB NOT NULL
        DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    CONSTRAINT location_dataset_points_latitude_check
        CHECK (
            latitude >= -90
            AND latitude <= 90
        ),

    CONSTRAINT location_dataset_points_longitude_check
        CHECK (
            longitude >= -180
            AND longitude <= 180
        ),

    CONSTRAINT location_dataset_points_dataset_source_unique
        UNIQUE (
            dataset_id,
            source_location_id
        )
);

CREATE INDEX location_dataset_points_dataset_id_idx
    ON location_dataset_points(dataset_id);

CREATE INDEX location_dataset_points_location_gix
    ON location_dataset_points
    USING GIST(location);