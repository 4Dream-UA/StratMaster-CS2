"""Add player_paths table and grenade trajectory coordinates

Revision ID: 0010_tactics_player
Revises: 0009_favorite_maps
Create Date: 2026-08-26 00:00:00
"""
from alembic import op

revision = "0010_tactics_player"
down_revision = "0009_favorite_maps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE grenades
        ADD COLUMN IF NOT EXISTS from_x DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS from_y DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS to_x DOUBLE PRECISION,
        ADD COLUMN IF NOT EXISTS to_y DOUBLE PRECISION;
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS player_paths (
            id UUID PRIMARY KEY,
            strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
            label VARCHAR(32) NOT NULL,
            color VARCHAR(16) NOT NULL DEFAULT '#ff9a00',
            waypoints JSONB NOT NULL DEFAULT '[]'::jsonb,
            "order" INTEGER NOT NULL DEFAULT 0
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS player_paths;")
    op.execute("""
        ALTER TABLE grenades
        DROP COLUMN IF EXISTS from_x,
        DROP COLUMN IF EXISTS from_y,
        DROP COLUMN IF EXISTS to_x,
        DROP COLUMN IF EXISTS to_y;
    """)
