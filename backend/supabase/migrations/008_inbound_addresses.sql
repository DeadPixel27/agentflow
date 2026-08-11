CREATE TABLE IF NOT EXISTS inbound_addresses (
    address_id TEXT PRIMARY KEY,
    full_address TEXT NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workflow_id UUID NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inbound_addresses_user_id
    ON inbound_addresses(user_id);
