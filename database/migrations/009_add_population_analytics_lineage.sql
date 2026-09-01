-- GeoVaris Coverage Intelligence
-- Migration 009: Add population analytics lineage
--
-- coverage_runs already contains:
--   covered_population
--   census_vintage
--
-- This migration adds the governed dataset and calculation-method
-- metadata required to make the population KPI reproducible and
-- understandable.
--
-- The initial MVP population method uses 2020 Census block population
-- allocated by the fraction of each block polygon intersected by the
-- coverage display geometry.
--
-- This is an estimate, not an exact count of people receiving service.

ALTER TABLE coverage_runs
    ADD COLUMN IF NOT EXISTS population_dataset_source TEXT,
    ADD COLUMN IF NOT EXISTS population_dataset_version TEXT,
    ADD COLUMN IF NOT EXISTS population_allocation_method TEXT,
    ADD COLUMN IF NOT EXISTS population_geometry_basis TEXT,
    ADD COLUMN IF NOT EXISTS population_intersecting_blocks INTEGER,
    ADD COLUMN IF NOT EXISTS population_fully_covered_blocks INTEGER,
    ADD COLUMN IF NOT EXISTS population_partially_covered_blocks INTEGER,
    ADD COLUMN IF NOT EXISTS population_calculated_at TIMESTAMPTZ;

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_population_intersecting_blocks_nonnegative
    CHECK (
        population_intersecting_blocks IS NULL
        OR population_intersecting_blocks >= 0
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_population_fully_covered_blocks_nonnegative
    CHECK (
        population_fully_covered_blocks IS NULL
        OR population_fully_covered_blocks >= 0
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_population_partially_covered_blocks_nonnegative
    CHECK (
        population_partially_covered_blocks IS NULL
        OR population_partially_covered_blocks >= 0
    );

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_population_block_counts_consistent
    CHECK (
        population_intersecting_blocks IS NULL
        OR population_fully_covered_blocks IS NULL
        OR population_partially_covered_blocks IS NULL
        OR population_intersecting_blocks =
            population_fully_covered_blocks +
            population_partially_covered_blocks
    );

CREATE INDEX IF NOT EXISTS idx_coverage_runs_population_calculated_at
    ON coverage_runs (
        population_calculated_at
    )
    WHERE population_calculated_at IS NOT NULL;

COMMENT ON COLUMN coverage_runs.covered_population IS
    'Estimated population covered by this coverage run. Calculation method and dataset lineage are stored in the population_* and census_vintage columns.';

COMMENT ON COLUMN coverage_runs.census_vintage IS
    'Census vintage associated with the population analytics result.';

COMMENT ON COLUMN coverage_runs.population_dataset_source IS
    'Authoritative population dataset source organization and dataset family.';

COMMENT ON COLUMN coverage_runs.population_dataset_version IS
    'Exact governed population dataset version used for this calculation.';

COMMENT ON COLUMN coverage_runs.population_allocation_method IS
    'Method used to allocate population for partially covered geography.';

COMMENT ON COLUMN coverage_runs.population_geometry_basis IS
    'Coverage representation used for the population calculation, such as display_geometry or authoritative_raster.';

COMMENT ON COLUMN coverage_runs.population_intersecting_blocks IS
    'Number of Census blocks with nonzero intersection with the coverage footprint.';

COMMENT ON COLUMN coverage_runs.population_fully_covered_blocks IS
    'Number of intersecting Census blocks treated as fully covered.';

COMMENT ON COLUMN coverage_runs.population_partially_covered_blocks IS
    'Number of intersecting Census blocks treated as partially covered.';

COMMENT ON COLUMN coverage_runs.population_calculated_at IS
    'Timestamp when population analytics were calculated for this coverage run.';