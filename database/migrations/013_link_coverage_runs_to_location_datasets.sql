-- GeoVaris Coverage Intelligence
-- Migration 013
--
-- Link coverage-run point-location analytics to the governed
-- location dataset used for the calculation.
--
-- This preserves exact dataset lineage while keeping the existing
-- Fabric KPI columns for backward compatibility.
--
-- Tenant isolation is enforced at the database relationship level:
-- the coverage run and location dataset must belong to the same
-- customer.

ALTER TABLE location_datasets
    ADD CONSTRAINT location_datasets_id_customer_unique
    UNIQUE (
        id,
        customer_id
    );

ALTER TABLE coverage_runs
    ADD COLUMN location_dataset_id UUID;

ALTER TABLE coverage_runs
    ADD CONSTRAINT coverage_runs_location_dataset_customer_fk
    FOREIGN KEY (
        location_dataset_id,
        customer_id
    )
    REFERENCES location_datasets (
        id,
        customer_id
    )
    ON DELETE RESTRICT;

CREATE INDEX idx_coverage_runs_location_dataset_id
    ON coverage_runs (
        location_dataset_id
    )
    WHERE location_dataset_id IS NOT NULL;

COMMENT ON COLUMN coverage_runs.location_dataset_id IS
    'Governed customer-scoped point-location dataset used for location coverage analytics. The referenced dataset must belong to the same customer as the coverage run.';