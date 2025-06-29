DROP TABLE IF EXISTS bulk_requests;

CREATE TABLE bulk_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_uuid TEXT NOT NULL UNIQUE,
    bank_account_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING, COMPLETED, FAILED
    total_amount_cents INTEGER NOT NULL DEFAULT 0,
    processed_amount_cents INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL
);

CREATE INDEX IF NOT EXISTS bulk_requests_request_uuid_idx ON bulk_requests (request_uuid);
