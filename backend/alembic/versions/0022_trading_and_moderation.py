"""User avatars, bans, trade blocking, case gift/sale offers

Revision ID: 0022_trading_and_moderation
Revises: 0021_forum_extras
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0022_trading_and_moderation"
down_revision = "0021_forum_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(512);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_trade_banned BOOLEAN NOT NULL DEFAULT false;")

    op.execute("""
        DO $$
        BEGIN
            BEGIN ALTER TYPE transactiontypeenum ADD VALUE IF NOT EXISTS 'case_gift'; EXCEPTION WHEN others THEN NULL; END;
            BEGIN ALTER TYPE transactiontypeenum ADD VALUE IF NOT EXISTS 'case_sale'; EXCEPTION WHEN others THEN NULL; END;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS wallet_trade_blocks (
            id UUID PRIMARY KEY,
            blocker_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            blocked_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE (blocker_user_id, blocked_user_id)
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS case_offers (
            id UUID PRIMARY KEY,
            sender_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            receiver_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL,
            price_coins INTEGER NOT NULL DEFAULT 0,
            offer_type VARCHAR(8) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_case_offers_receiver ON case_offers (receiver_user_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_case_offers_sender ON case_offers (sender_user_id, status);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS case_offers;")
    op.execute("DROP TABLE IF EXISTS wallet_trade_blocks;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_trade_banned;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_banned;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS avatar_url;")
