"""Add forum_categories, forum_threads, forum_posts + seed lounge/support

Revision ID: 0017_forum
Revises: 0016_case_english_name
Create Date: 2026-08-29 00:00:00
"""
import uuid

from alembic import op

revision = "0017_forum"
down_revision = "0016_case_english_name"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_categories (
            id UUID PRIMARY KEY,
            key VARCHAR(32) NOT NULL UNIQUE,
            name VARCHAR(64) NOT NULL,
            description VARCHAR(256) NOT NULL
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_threads (
            id UUID PRIMARY KEY,
            category_id UUID NOT NULL REFERENCES forum_categories(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(128) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_posts (
            id UUID PRIMARY KEY,
            thread_id UUID NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            body TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_forum_threads_category_id ON forum_threads (category_id);
        CREATE INDEX IF NOT EXISTS ix_forum_threads_user_id ON forum_threads (user_id);
        CREATE INDEX IF NOT EXISTS ix_forum_posts_thread_id ON forum_posts (thread_id);
    """)

    op.execute(f"""
        INSERT INTO forum_categories (id, key, name, description) VALUES
            ('{uuid.uuid4()}', 'lounge', 'Lounge', 'Off-topic chat for premium players — talk CS2, teams, whatever.'),
            ('{uuid.uuid4()}', 'support', 'Support', 'Get help from the team — your own private ticket, just you and admins.')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forum_posts;")
    op.execute("DROP TABLE IF EXISTS forum_threads;")
    op.execute("DROP TABLE IF EXISTS forum_categories;")
