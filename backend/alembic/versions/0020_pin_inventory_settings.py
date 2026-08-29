"""Forum thread pinning, case inventory (buy/open split), app settings

Revision ID: 0020_pin_inventory_settings
Revises: 0019_case_rebalance
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0020_pin_inventory_settings"
down_revision = "0019_case_rebalance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE forum_threads ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT false;")

    op.execute("""
        CREATE TABLE IF NOT EXISTS case_inventory (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            acquired_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_case_inventory_user_case ON case_inventory (user_id, case_id);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY,
            logo_url VARCHAR(512)
        );
    """)
    op.execute("INSERT INTO app_settings (id, logo_url) VALUES (1, NULL) ON CONFLICT (id) DO NOTHING;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS app_settings;")
    op.execute("DROP TABLE IF EXISTS case_inventory;")
    op.execute("ALTER TABLE forum_threads DROP COLUMN IF EXISTS is_pinned;")
