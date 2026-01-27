-- Migration 016: store YClients visits locally

ALTER TABLE users
ADD COLUMN IF NOT EXISTS visits_last_sync TIMESTAMP WITH TIME ZONE;

CREATE TABLE IF NOT EXISTS yclients_visits (
    id BIGSERIAL PRIMARY KEY,
    visit_id INT UNIQUE NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(id),
    yclients_client_id INT,
    visit_datetime TIMESTAMP WITH TIME ZONE,
    amount NUMERIC,
    status TEXT,
    master TEXT,
    services JSONB,
    raw_payload JSONB,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_yclients_visits_user_id
    ON yclients_visits(user_id);

CREATE INDEX IF NOT EXISTS idx_yclients_visits_visit_datetime
    ON yclients_visits(visit_datetime);

CREATE INDEX IF NOT EXISTS idx_yclients_visits_client_id
    ON yclients_visits(yclients_client_id);
