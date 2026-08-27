"""Add personal_boards, personal_board_paths, personal_board_grenades tables

Revision ID: 0012_personal_boards
Revises: 0011_favorite_strategies
Create Date: 2026-08-27 00:00:00
"""
from alembic import op

revision = "0012_personal_boards"
down_revision = "0011_favorite_strategies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS personal_boards (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            map_id INTEGER NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
            title VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS personal_board_paths (
            id UUID PRIMARY KEY,
            board_id UUID NOT NULL REFERENCES personal_boards(id) ON DELETE CASCADE,
            label VARCHAR(32) NOT NULL,
            color VARCHAR(16) NOT NULL DEFAULT '#ff9a00',
            waypoints JSONB NOT NULL,
            "order" INTEGER NOT NULL DEFAULT 0
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS personal_board_grenades (
            id UUID PRIMARY KEY,
            board_id UUID NOT NULL REFERENCES personal_boards(id) ON DELETE CASCADE,
            grenade_type grenadetypeenum NOT NULL,
            target VARCHAR(64) NOT NULL,
            "order" INTEGER NOT NULL DEFAULT 0,
            from_x FLOAT,
            from_y FLOAT,
            to_x FLOAT,
            to_y FLOAT
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS personal_board_grenades;")
    op.execute("DROP TABLE IF EXISTS personal_board_paths;")
    op.execute("DROP TABLE IF EXISTS personal_boards;")
