"""Premium-day vouchers land in inventory instead of applying instantly

Revision ID: 0030_premium_vouchers
Revises: 0029_forum_overhaul_and_profile
Create Date: 2026-08-31 00:00:00
"""
from alembic import op

revision = "0030_premium_vouchers"
down_revision = "0029_forum_overhaul_and_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS premium_vouchers (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            days INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_premium_vouchers_user ON premium_vouchers (user_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS premium_voucher_offers (
            id UUID PRIMARY KEY,
            sender_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receiver_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            days INTEGER NOT NULL,
            price_coins INTEGER NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_premium_voucher_offers_receiver ON premium_voucher_offers (receiver_user_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_premium_voucher_offers_sender ON premium_voucher_offers (sender_user_id, status);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS premium_voucher_offers;")
    op.execute("DROP TABLE IF EXISTS premium_vouchers;")
