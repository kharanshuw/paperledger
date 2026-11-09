-- Migration 003: Create statements and primary confirmed transactions ledger

CREATE TABLE IF NOT EXISTS statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    file_hash VARCHAR(64) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(512) NOT NULL,
    status statement_status NOT NULL DEFAULT 'QUEUED',
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_statements_user_id ON statements(user_id);
CREATE INDEX IF NOT EXISTS ix_statements_account_id ON statements(account_id);
CREATE INDEX IF NOT EXISTS ix_statements_status ON statements(status);
CREATE INDEX IF NOT EXISTS ix_statements_user_file_hash ON statements(user_id, file_hash);

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    statement_id UUID REFERENCES statements(id) ON DELETE SET NULL,
    amount NUMERIC(12, 2) NOT NULL,
    transaction_type transaction_type NOT NULL,
    transaction_date DATE NOT NULL,
    raw_description TEXT NOT NULL,
    clean_merchant VARCHAR(255),
    is_reviewed BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_account_id ON transactions(account_id);
CREATE INDEX IF NOT EXISTS ix_transactions_category_id ON transactions(category_id);
CREATE INDEX IF NOT EXISTS ix_transactions_statement_id ON transactions(statement_id);
CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS ix_transactions_clean_merchant ON transactions(clean_merchant);
CREATE INDEX IF NOT EXISTS ix_transactions_user_date ON transactions(user_id, transaction_date);
CREATE INDEX IF NOT EXISTS ix_transactions_account_date ON transactions(account_id, transaction_date);
CREATE INDEX IF NOT EXISTS ix_transactions_account_amount_date ON transactions(account_id, amount, transaction_date);
