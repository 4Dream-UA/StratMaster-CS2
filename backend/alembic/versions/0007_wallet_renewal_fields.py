"""Add lifetime/auto-renew/reminder tracking columns to wallets

Revision ID: 0007_wallet_renewal_fields
Revises: 0006_promo_redemptions
Create Date: 2026-07-29 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_wallet_renewal_fields"
down_revision = "0006_promo_redemptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE wallets
        ADD COLUMN IF NOT EXISTS is_lifetime BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE wallets
        ADD COLUMN IF NOT EXISTS last_plan_months INTEGER;
    """)
    op.execute("""
        ALTER TABLE wallets
        ADD COLUMN IF NOT EXISTS auto_renew BOOLEAN NOT NULL DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE wallets
        ADD COLUMN IF NOT EXISTS reminder_sent_for_expiry TIMESTAMP WITH TIME ZONE;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS reminder_sent_for_expiry;")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS auto_renew;")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS last_plan_months;")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS is_lifetime;")
