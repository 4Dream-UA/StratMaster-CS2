"""Add crypto_invoices table for CryptoPay checkout tracking

Revision ID: 0008_crypto_invoices
Revises: 0007_wallet_renewal_fields
Create Date: 2026-08-26 00:00:00
"""
from alembic import op

revision = "0008_crypto_invoices"
down_revision = "0007_wallet_renewal_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS crypto_invoices (
            id UUID PRIMARY KEY,
            invoice_id INTEGER NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            coins INTEGER NOT NULL,
            plan VARCHAR(16),
            months INTEGER,
            amount_usd VARCHAR(16) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            paid_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_crypto_invoices_invoice_id
        ON crypto_invoices (invoice_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS crypto_invoices;")
