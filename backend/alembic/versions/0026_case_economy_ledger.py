"""Case economy: premium-days openings + a shared spent/paid ledger

Revision ID: 0026_case_economy_ledger
Revises: 0025_admin_grant_coins
Create Date: 2026-08-30 00:00:00
"""
from alembic import op

revision = "0026_case_economy_ledger"
down_revision = "0025_admin_grant_coins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE case_openings ADD COLUMN IF NOT EXISTS premium_days_won INTEGER;")
    op.execute("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS case_total_spent_coins INTEGER NOT NULL DEFAULT 0;")
    op.execute("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS case_total_paid_coins INTEGER NOT NULL DEFAULT 0;")


def downgrade() -> None:
    op.execute("ALTER TABLE app_settings DROP COLUMN IF EXISTS case_total_paid_coins;")
    op.execute("ALTER TABLE app_settings DROP COLUMN IF EXISTS case_total_spent_coins;")
    op.execute("ALTER TABLE case_openings DROP COLUMN IF EXISTS premium_days_won;")
