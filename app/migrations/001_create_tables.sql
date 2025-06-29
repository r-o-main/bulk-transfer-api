DROP TABLE IF EXISTS bank_accounts;

CREATE TABLE bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_name TEXT NOT NULL,
    iban TEXT NOT NULL,
    bic TEXT NOT NULL,
    balance_cents INTEGER NOT NULL,
    ongoing_transfer_cents INTEGER NOT NULL
);

INSERT INTO bank_accounts VALUES(1,'ACME Corp','FR10474608000002006107XXXXX','OIVUSCLQXXX',10000000,0);

DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_uuid TEXT NOT NULL UNIQUE,
    bulk_request_uuid TEXT NULL DEFAULT NULL,
    counterparty_name TEXT NOT NULL,
    counterparty_iban TEXT NOT NULL,
    counterparty_bic TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    amount_currency TEXT NOT NULL,
    bank_account_id INTEGER NOT NULL,
    description TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS transactions_bank_account_id_idx ON transactions (bank_account_id);

INSERT INTO transactions VALUES(1, 'd452fb50-1f62-445e-b705-78a9a07855c8', null, 'ACME Corp. Main Account','EE382200221020145685','CCOPFRPPXXX',11000000,'EUR',1,'Treasury income');
INSERT INTO transactions VALUES(2, 'e911a0df-b61c-4703-82d2-2e2bbfff1770', null, 'Bip Bip','EE383680981021245685','CRLYFRPPTOU',-1000000,'EUR',1,'Bip Bip Salary');

