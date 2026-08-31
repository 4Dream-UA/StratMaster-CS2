"""AI support agent — a system user it posts as, plus an admin kill switch

The agent needs a real users row because forum_posts.user_id is NOT NULL and
every post-rendering path walks through it. telegram_id 0 is the sentinel:
Telegram ids are always positive, so it can never collide with a real
account, and the row is unreachable through the auth flow.

Revision ID: 0035_ai_support_agent
Revises: 0034_forum_thread_reports
Create Date: 2026-08-31 00:00:05
"""
import uuid

from alembic import op

revision = "0035_ai_support_agent"
down_revision = "0034_forum_thread_reports"
branch_labels = None
depends_on = None

AGENT_TELEGRAM_ID = 0
AGENT_USERNAME = "stratmaster_ai"
AGENT_DISPLAY_NAME = "StratMaster Assistant"


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_ai_agent BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE app_settings ADD COLUMN IF NOT EXISTS ai_agent_enabled BOOLEAN NOT NULL DEFAULT true;")

    agent_id = uuid.uuid4()
    wallet_row_id = uuid.uuid4()
    # A wallet is created alongside it purely so the agent row is shaped like
    # every other user — plenty of code reaches for user.wallet without
    # checking, and a missing one would be an AttributeError waiting to
    # happen. It never holds coins and never trades.
    op.execute(f"""
        INSERT INTO users (id, telegram_id, username, display_name, is_admin, is_banned, is_trade_banned,
                           hide_username_on_forum, is_ai_agent, created_at)
        VALUES ('{agent_id}', {AGENT_TELEGRAM_ID}, '{AGENT_USERNAME}', '{AGENT_DISPLAY_NAME}',
                false, false, true, false, true, NOW())
        ON CONFLICT (telegram_id) DO UPDATE SET is_ai_agent = true;
    """)
    op.execute(f"""
        INSERT INTO wallets (id, user_id, wallet_id, balance_coins, is_lifetime, auto_renew, auto_renew_method)
        SELECT '{wallet_row_id}', u.id, 'AIAGENT000000000', 0, false, false, 'mastercoins'
        FROM users u WHERE u.telegram_id = {AGENT_TELEGRAM_ID}
        ON CONFLICT (user_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute(f"DELETE FROM users WHERE telegram_id = {AGENT_TELEGRAM_ID} AND is_ai_agent = true;")
    op.execute("ALTER TABLE app_settings DROP COLUMN IF EXISTS ai_agent_enabled;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_ai_agent;")
