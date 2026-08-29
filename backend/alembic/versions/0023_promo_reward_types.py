"""Promo code reward types: premium days and cases, alongside MasterCoins

Revision ID: 0023_promo_reward_types
Revises: 0022_trading_and_moderation
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0023_promo_reward_types"
down_revision = "0022_trading_and_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS reward_type VARCHAR(16) NOT NULL DEFAULT 'coins';")
    op.execute("ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS premium_days INTEGER;")
    op.execute("ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS case_id UUID REFERENCES cases(id) ON DELETE SET NULL;")
    op.execute("ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS case_quantity INTEGER NOT NULL DEFAULT 1;")


def downgrade() -> None:
    op.execute("ALTER TABLE promo_codes DROP COLUMN IF EXISTS case_quantity;")
    op.execute("ALTER TABLE promo_codes DROP COLUMN IF EXISTS case_id;")
    op.execute("ALTER TABLE promo_codes DROP COLUMN IF EXISTS premium_days;")
    op.execute("ALTER TABLE promo_codes DROP COLUMN IF EXISTS reward_type;")
