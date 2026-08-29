"""Forum: ticket closing, share links, thread watching, reply-to-post

Revision ID: 0021_forum_extras
Revises: 0020_pin_inventory_settings
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0021_forum_extras"
down_revision = "0020_pin_inventory_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE forum_threads ADD COLUMN IF NOT EXISTS is_closed BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE forum_threads ADD COLUMN IF NOT EXISTS share_token VARCHAR(24) UNIQUE;")
    op.execute("ALTER TABLE forum_posts ADD COLUMN IF NOT EXISTS reply_to_post_id UUID REFERENCES forum_posts(id) ON DELETE SET NULL;")

    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_thread_watchers (
            id UUID PRIMARY KEY,
            thread_id UUID NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (thread_id, user_id)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_forum_thread_watchers_thread ON forum_thread_watchers (thread_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forum_thread_watchers;")
    op.execute("ALTER TABLE forum_posts DROP COLUMN IF EXISTS reply_to_post_id;")
    op.execute("ALTER TABLE forum_threads DROP COLUMN IF EXISTS share_token;")
    op.execute("ALTER TABLE forum_threads DROP COLUMN IF EXISTS is_closed;")
