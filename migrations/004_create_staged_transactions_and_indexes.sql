-- Migration 004: Create staged_transactions table for PDF parsing buffer

CREATE TABLE IF NOT EXISTS staged_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_id UUID NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
    suggested_category_id UUID REFERENCES categories(id) ON DELETE SET NULL,
    amount NUMERIC(12, 2) NOT NULL,
    transaction_type transaction_type NOT NULL,
    transaction_date DATE NOT NULL,
    raw_description TEXT NOT NULL,
    clean_merchant VARCHAR(255),
    potential_duplicate_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    duplicate_confidence NUMERIC(3, 2),
    status staged_status NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_staged_transactions_statement_id ON staged_transactions(statement_id);
CREATE INDEX IF NOT EXISTS ix_staged_transactions_status ON staged_transactions(status);
CREATE INDEX IF NOT EXISTS ix_staged_transactions_potential_duplicate ON staged_transactions(potential_duplicate_id);
CREATE INDEX IF NOT EXISTS ix_staged_transactions_statement_status ON staged_transactions(statement_id, status);
