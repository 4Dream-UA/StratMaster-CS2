"""Emoji reactions on forum posts

Revision ID: 0028_forum_reactions
Revises: 0027_case_economy_rebalance
Create Date: 2026-08-30 00:00:00
"""
from alembic import op

revision = "0028_forum_reactions"
down_revision = "0027_case_economy_rebalance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_post_reactions (
            id UUID PRIMARY KEY,
            post_id UUID NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            emoji VARCHAR(8) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            UNIQUE (post_id, user_id, emoji)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_forum_post_reactions_post ON forum_post_reactions (post_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forum_post_reactions;")
