-- GeoVaris Coverage Intelligence
-- Migration 005: Snapshot NTIA ITM parameters into coverage runs
--
-- These fields preserve the propagation-model assumptions used for
-- reproducibility. They are nullable so existing free-space development
-- runs remain valid.

ALTER TABLE coverage_runs
    ADD COLUMN IF NOT EXISTS itm_climate INTEGER,
    ADD COLUMN IF NOT EXISTS itm_polarization INTEGER,
    ADD COLUMN IF NOT EXISTS itm_variability_mode INTEGER,
    ADD COLUMN IF NOT EXISTS itm_surface_refractivity DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS itm_dielectric_constant DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS itm_conductivity_s_per_m DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS itm_confidence DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS itm_reliability DOUBLE PRECISION;

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_climate_valid
    CHECK (
        itm_climate IS NULL
        OR itm_climate BETWEEN 1 AND 7
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_polarization_valid
    CHECK (
        itm_polarization IS NULL
        OR itm_polarization IN (0, 1)
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_variability_mode_valid
    CHECK (
        itm_variability_mode IS NULL
        OR itm_variability_mode BETWEEN 0 AND 3
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_surface_refractivity_valid
    CHECK (
        itm_surface_refractivity IS NULL
        OR (
            itm_surface_refractivity >= 250
            AND itm_surface_refractivity <= 400
        )
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_dielectric_constant_valid
    CHECK (
        itm_dielectric_constant IS NULL
        OR itm_dielectric_constant > 1
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_conductivity_valid
    CHECK (
        itm_conductivity_s_per_m IS NULL
        OR itm_conductivity_s_per_m > 0
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_confidence_valid
    CHECK (
        itm_confidence IS NULL
        OR (
            itm_confidence > 0
            AND itm_confidence < 1
        )
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_itm_reliability_valid
    CHECK (
        itm_reliability IS NULL
        OR (
            itm_reliability > 0
            AND itm_reliability < 1
        )
    );