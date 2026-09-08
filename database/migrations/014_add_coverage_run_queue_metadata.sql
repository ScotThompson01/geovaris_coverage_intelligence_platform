/*
 * GeoVaris Coverage Intelligence
 *
 * Migration 014
 *
 * Add production job-queue metadata to coverage_runs.
 *
 * This migration is intentionally additive.
 *
 * It does not change the existing coverage run status model:
 *
 *   pending
 *   processing
 *   completed
 *   failed
 *
 * Existing workers may continue operating after this migration.
 *
 * The new fields provide the metadata needed for:
 *
 * - retry accounting
 * - delayed retry scheduling
 * - worker ownership
 * - stale-job detection
 * - worker heartbeat tracking
 * - failure timing
 *
 * Actual retry and recovery behavior is implemented separately
 * in worker code.
 */


ALTER TABLE coverage_runs
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER
        NOT NULL
        DEFAULT 0,

    ADD COLUMN IF NOT EXISTS max_attempts INTEGER
        NOT NULL
        DEFAULT 3,

    ADD COLUMN IF NOT EXISTS next_attempt_at TIMESTAMPTZ,

    ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ,

    ADD COLUMN IF NOT EXISTS claimed_by TEXT,

    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ,

    ADD COLUMN IF NOT EXISTS last_error_at TIMESTAMPTZ;


/*
 * Queue counters must remain internally valid.
 *
 * Use DO blocks so the migration remains safe if a constraint
 * already exists in an environment where the migration has been
 * partially applied.
 */

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname =
            'coverage_runs_attempt_count_nonnegative'
    ) THEN
        ALTER TABLE coverage_runs
            ADD CONSTRAINT
                coverage_runs_attempt_count_nonnegative
            CHECK (
                attempt_count >= 0
            );
    END IF;
END
$$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname =
            'coverage_runs_max_attempts_positive'
    ) THEN
        ALTER TABLE coverage_runs
            ADD CONSTRAINT
                coverage_runs_max_attempts_positive
            CHECK (
                max_attempts > 0
            );
    END IF;
END
$$;


DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname =
            'coverage_runs_attempt_count_within_limit'
    ) THEN
        ALTER TABLE coverage_runs
            ADD CONSTRAINT
                coverage_runs_attempt_count_within_limit
            CHECK (
                attempt_count <= max_attempts
            );
    END IF;
END
$$;


/*
 * Pending-run queue index.
 *
 * The current workers select:
 *
 *   status = 'pending'
 *   propagation_model = ...
 *   ORDER BY created_at
 *
 * Future production claiming will also consider next_attempt_at.
 */

CREATE INDEX IF NOT EXISTS
    idx_coverage_runs_pending_queue
ON coverage_runs (
    propagation_model,
    next_attempt_at,
    created_at
)
WHERE status = 'pending';


/*
 * Processing-run index used by future stale-worker recovery.
 */

CREATE INDEX IF NOT EXISTS
    idx_coverage_runs_processing_heartbeat
ON coverage_runs (
    heartbeat_at
)
WHERE status = 'processing';


COMMENT ON COLUMN coverage_runs.attempt_count IS
    'Number of worker processing attempts claimed for this coverage run.';


COMMENT ON COLUMN coverage_runs.max_attempts IS
    'Maximum number of worker processing attempts permitted before the run remains failed.';


COMMENT ON COLUMN coverage_runs.next_attempt_at IS
    'Earliest timestamp when a pending coverage run is eligible to be claimed for another processing attempt. NULL means immediately eligible.';


COMMENT ON COLUMN coverage_runs.claimed_at IS
    'Timestamp when the current or most recent worker claimed this coverage run.';


COMMENT ON COLUMN coverage_runs.claimed_by IS
    'Identifier of the worker process that claimed the current or most recent processing attempt.';


COMMENT ON COLUMN coverage_runs.heartbeat_at IS
    'Most recent heartbeat timestamp recorded by the worker processing this coverage run. Used for stale-job detection and recovery.';


COMMENT ON COLUMN coverage_runs.last_error_at IS
    'Timestamp of the most recent worker processing error for this coverage run.';