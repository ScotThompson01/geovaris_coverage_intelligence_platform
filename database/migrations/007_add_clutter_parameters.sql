-- GeoVaris Coverage Intelligence
-- Migration 007: Store clutter dataset and model parameters
--
-- Clutter dataset lineage and clutter-model assumptions belong to the
-- scenario definition and are snapshotted into each coverage run so
-- calculations remain reproducible.
--
-- Existing scenarios and historical coverage runs remain valid because
-- all fields are nullable.
--
-- clutter_source / clutter_version describe the governed land-cover
-- dataset, for example Annual NLCD 2025.
--
-- clutter_model / clutter_model_version describe the RF clutter model,
-- for example ITU-R P.2108-1.
--
-- clutter_percentage_locations and clutter_correction_end preserve the
-- statistical/model configuration used by the calculation.

ALTER TABLE scenarios
    ADD COLUMN IF NOT EXISTS clutter_source TEXT,
    ADD COLUMN IF NOT EXISTS clutter_version TEXT,
    ADD COLUMN IF NOT EXISTS clutter_model TEXT,
    ADD COLUMN IF NOT EXISTS clutter_model_version TEXT,
    ADD COLUMN IF NOT EXISTS clutter_percentage_locations DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS clutter_correction_end TEXT;

ALTER TABLE coverage_runs
    ADD COLUMN IF NOT EXISTS clutter_source TEXT,
    ADD COLUMN IF NOT EXISTS clutter_version TEXT,
    ADD COLUMN IF NOT EXISTS clutter_model TEXT,
    ADD COLUMN IF NOT EXISTS clutter_model_version TEXT,
    ADD COLUMN IF NOT EXISTS clutter_percentage_locations DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS clutter_correction_end TEXT;


ALTER TABLE scenarios
    ADD CONSTRAINT scenarios_clutter_percentage_locations_valid
    CHECK (
        clutter_percentage_locations IS NULL
        OR (
            clutter_percentage_locations > 0
            AND clutter_percentage_locations < 100
        )
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_clutter_percentage_locations_valid
    CHECK (
        clutter_percentage_locations IS NULL
        OR (
            clutter_percentage_locations > 0
            AND clutter_percentage_locations < 100
        )
    );


ALTER TABLE scenarios
    ADD CONSTRAINT scenarios_clutter_correction_end_valid
    CHECK (
        clutter_correction_end IS NULL
        OR clutter_correction_end IN (
            'transmitter',
            'receiver',
            'both'
        )
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_clutter_correction_end_valid
    CHECK (
        clutter_correction_end IS NULL
        OR clutter_correction_end IN (
            'transmitter',
            'receiver',
            'both'
        )
    );