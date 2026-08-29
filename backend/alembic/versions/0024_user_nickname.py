"""User display name (nickname), shown big/primary next to the small @username

Revision ID: 0024_user_nickname
Revises: 0023_promo_reward_types
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0024_user_nickname"
down_revision = "0023_promo_reward_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(32);")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS display_name;")
