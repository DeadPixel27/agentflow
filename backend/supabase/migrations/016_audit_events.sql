-- Append-only activity log (who did what). Not for document payloads.

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    request_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_audit_events_actor_date
    ON audit_events(actor_user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_events_action_date
    ON audit_events(action, created_at);
