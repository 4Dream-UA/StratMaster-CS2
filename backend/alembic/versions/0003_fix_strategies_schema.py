"""Add created_at and remaining missing columns to strategies

Revision ID: 0003_fix_strategies_schema
Revises: 0002_add_missing_columns
Create Date: 2024-01-03 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_fix_strategies_schema"
down_revision = "0002_add_missing_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # created_at — самая частая потеря из старой миграции
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW();
    """)

    # roles_description — на случай если тоже отсутствует
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS roles_description TEXT;
    """)

    # difficulty_stars default
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS difficulty_stars INTEGER NOT NULL DEFAULT 3;
    """)

    # success_rate default
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS success_rate INTEGER NOT NULL DEFAULT 75;
    """)

    # author
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS author VARCHAR(64);
    """)

    # is_free
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS is_free BOOLEAN NOT NULL DEFAULT FALSE;
    """)

    # grenades.target — если ещё destination
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='grenades' AND column_name='destination'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='grenades' AND column_name='target'
            ) THEN
                ALTER TABLE grenades RENAME COLUMN destination TO target;
            END IF;
        END $$;
    """)

    op.execute("""
        ALTER TABLE grenades
        ADD COLUMN IF NOT EXISTS target VARCHAR(64) NOT NULL DEFAULT '';
    """)

    op.execute("""
        ALTER TABLE grenades
        ADD COLUMN IF NOT EXISTS timing VARCHAR(16) NOT NULL DEFAULT '0:00';
    """)

    op.execute("""
        ALTER TABLE grenades
        ADD COLUMN IF NOT EXISTS video_url VARCHAR(512);
    """)

    op.execute("""
        ALTER TABLE grenades
        ADD COLUMN IF NOT EXISTS "order" INTEGER NOT NULL DEFAULT 0;
    """)

    # images table — если называется strategy_images
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name='strategy_images'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.tables WHERE table_name='images'
            ) THEN
                ALTER TABLE strategy_images RENAME TO images;
            END IF;
        END $$;
    """)

    op.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS "order" INTEGER NOT NULL DEFAULT 0;
    """)


def downgrade() -> None:
    pass