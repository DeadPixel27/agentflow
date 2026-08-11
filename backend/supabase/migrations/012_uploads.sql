-- Uploads registry — bind upload_id to owning user (IDOR prevention)

CREATE TABLE IF NOT EXISTS uploads (
    id text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);

-- Best-effort backfill from prior runs (prefer run.user_id, else workflow owner)
INSERT INTO uploads (id, user_id)
SELECT DISTINCT ON (wr.upload_id)
    wr.upload_id,
    COALESCE(wr.user_id, w.user_id)
FROM workflow_runs wr
LEFT JOIN workflows w ON w.id = wr.workflow_id
WHERE COALESCE(wr.user_id, w.user_id) IS NOT NULL
ORDER BY wr.upload_id, wr.created_at DESC
ON CONFLICT (id) DO NOTHING;
