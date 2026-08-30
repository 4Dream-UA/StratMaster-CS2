"""Forum edit history, soft delete, whisper posts, expanded reactions; user profile info

Revision ID: 0029_forum_overhaul_and_profile
Revises: 0028_forum_reactions
Create Date: 2026-08-30 00:00:00
"""
from alembic import op

revision = "0029_forum_overhaul_and_profile"
down_revision = "0028_forum_reactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS hide_username_on_forum BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS profile_info JSONB;
    """)
    op.execute("""
        ALTER TABLE forum_posts
        ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS edited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS deleted_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS visible_to_user_ids JSONB;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_post_edits (
            id UUID PRIMARY KEY,
            post_id UUID NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
            editor_id UUID REFERENCES users(id) ON DELETE SET NULL,
            previous_body TEXT NOT NULL,
            edited_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_forum_post_edits_post ON forum_post_edits (post_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forum_post_edits;")
    op.execute("""
        ALTER TABLE forum_posts
        DROP COLUMN IF EXISTS edited_at,
        DROP COLUMN IF EXISTS edited_by_id,
        DROP COLUMN IF EXISTS deleted_at,
        DROP COLUMN IF EXISTS deleted_by_id,
        DROP COLUMN IF EXISTS visible_to_user_ids;
    """)
    op.execute("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS hide_username_on_forum,
        DROP COLUMN IF EXISTS profile_info;
    """)
