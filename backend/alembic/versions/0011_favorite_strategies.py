"""Add favorite_strategies table

Revision ID: 0011_favorite_strategies
Revises: 0010_tactics_player
Create Date: 2026-08-26 00:00:00
"""
from alembic import op

revision = "0011_favorite_strategies"
down_revision = "0010_tactics_player"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS favorite_strategies (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_favorite_user_strategy UNIQUE (user_id, strategy_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS favorite_strategies;")
