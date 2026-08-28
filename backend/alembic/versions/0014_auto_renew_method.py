"""Add wallets.auto_renew_method

Revision ID: 0014_auto_renew_method
Revises: 0013_board_sharing
Create Date: 2026-08-27 00:00:00
"""
from alembic import op

revision = "0014_auto_renew_method"
down_revision = "0013_board_sharing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE wallets
        ADD COLUMN IF NOT EXISTS auto_renew_method VARCHAR(16) NOT NULL DEFAULT 'mastercoins';
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS auto_renew_method;")
