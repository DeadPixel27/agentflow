-- Launch tables: usage tracking, waitlist, analytics, admin flag

-- Usage events - track page extractions per user
CREATE TABLE IF NOT EXISTS usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pages INT NOT NULL DEFAULT 1,
    template_id TEXT,
    run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL DEFAULT 'extraction',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_month
    ON usage_events(user_id, created_at);

-- Waitlist - collect Pro tier interest
CREATE TABLE IF NOT EXISTS waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'pricing_page',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_waitlist_email
    ON waitlist(email);

-- Analytics events - track product usage
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    template_id TEXT,
    run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    duration_ms INT,
    page_count INT,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_type_date
    ON analytics_events(event_type, created_at);

-- Add admin flag to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;
