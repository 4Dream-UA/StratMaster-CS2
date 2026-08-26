"""Add favorite_maps table

Revision ID: 0009_favorite_maps
Revises: 0008_crypto_invoices
Create Date: 2026-08-26 00:00:00
"""
from alembic import op

revision = "0009_favorite_maps"
down_revision = "0008_crypto_invoices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS favorite_maps (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            map_id INTEGER NOT NULL REFERENCES maps(id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_favorite_user_map UNIQUE (user_id, map_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS favorite_maps;")
