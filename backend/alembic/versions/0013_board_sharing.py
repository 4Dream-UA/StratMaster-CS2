"""Add personal_boards.share_token + personal_board_collaborator_link

Revision ID: 0013_board_sharing
Revises: 0012_personal_boards
Create Date: 2026-08-27 00:00:00
"""
from alembic import op

revision = "0013_board_sharing"
down_revision = "0012_personal_boards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE personal_boards ADD COLUMN IF NOT EXISTS share_token VARCHAR(24);
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_personal_boards_share_token
        ON personal_boards (share_token) WHERE share_token IS NOT NULL;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS personal_board_collaborator_link (
            board_id UUID NOT NULL REFERENCES personal_boards(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            PRIMARY KEY (board_id, user_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS personal_board_collaborator_link;")
    op.execute("DROP INDEX IF EXISTS ix_personal_boards_share_token;")
    op.execute("ALTER TABLE personal_boards DROP COLUMN IF EXISTS share_token;")
