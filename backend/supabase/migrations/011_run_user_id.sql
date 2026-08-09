-- Add user_id to workflow_runs for ownership + metering linkage

ALTER TABLE workflow_runs
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id
    ON workflow_runs(user_id);

-- Backfill from usage_events when available
UPDATE workflow_runs wr
SET user_id = ue.user_id
FROM (
    SELECT DISTINCT ON (run_id) run_id, user_id
    FROM usage_events
    WHERE run_id IS NOT NULL AND user_id IS NOT NULL
    ORDER BY run_id, created_at DESC
) ue
WHERE wr.id = ue.run_id
  AND wr.user_id IS NULL;

-- Backfill from parent workflow owner
UPDATE workflow_runs wr
SET user_id = w.user_id
FROM workflows w
WHERE wr.workflow_id = w.id
  AND wr.user_id IS NULL
  AND w.user_id IS NOT NULL;
