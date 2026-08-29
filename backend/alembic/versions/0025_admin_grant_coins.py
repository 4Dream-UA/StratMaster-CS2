"""Add admin_grant transaction type for the admin coin-grant control

Revision ID: 0025_admin_grant_coins
Revises: 0024_user_nickname
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0025_admin_grant_coins"
down_revision = "0024_user_nickname"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            BEGIN ALTER TYPE transactiontypeenum ADD VALUE IF NOT EXISTS 'admin_grant'; EXCEPTION WHEN others THEN NULL; END;
        END $$;
    """)


def downgrade() -> None:
    pass
