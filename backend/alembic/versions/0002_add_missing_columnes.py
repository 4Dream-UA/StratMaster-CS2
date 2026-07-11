"""Add missing columns to existing tables

Revision ID: 0002_add_missing_columns
Revises: 0001_init
Create Date: 2024-01-02 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_add_missing_columns"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── strategies: add timings_description if missing ────────────
    op.execute("""
        ALTER TABLE strategies
        ADD COLUMN IF NOT EXISTS timings_description TEXT;
    """)

    # ── strategies: rename destination→target in grenades ─────────
    # Старая миграция создавала колонку 'destination', модель ждёт 'target'
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='grenades' AND column_name='destination'
            ) THEN
                ALTER TABLE grenades RENAME COLUMN destination TO target;
            END IF;
        END $$;
    """)

    # ── grenades: add timing NOT NULL default '' если не существует ─
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='grenades' AND column_name='timing'
            ) THEN
                ALTER TABLE grenades ADD COLUMN timing VARCHAR(16) NOT NULL DEFAULT '0:00';
            END IF;
        END $$;
    """)

    # ── grenades: add video_url если не существует ─────────────────
    op.execute("""
        ALTER TABLE grenades
        ADD COLUMN IF NOT EXISTS video_url VARCHAR(512);
    """)

    # ── grenades: rename lineup_url→video_url если осталось старое имя
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='grenades' AND column_name='lineup_url'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='grenades' AND column_name='video_url'
            ) THEN
                ALTER TABLE grenades RENAME COLUMN lineup_url TO video_url;
            END IF;
        END $$;
    """)

    # ── strategy_images → images: если таблица называется по-старому
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name='strategy_images'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name='images'
            ) THEN
                ALTER TABLE strategy_images RENAME TO images;
            END IF;
        END $$;
    """)

    # ── images: rename is_main→order если нужно ───────────────────
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='images' AND column_name='is_main'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='images' AND column_name='order'
            ) THEN
                ALTER TABLE images ADD COLUMN "order" INTEGER NOT NULL DEFAULT 0;
            END IF;
        END $$;
    """)

    # ── buy_tags: создать если не существует ──────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS buy_tags (
            id SERIAL PRIMARY KEY,
            name VARCHAR(32) UNIQUE NOT NULL
        );
    """)

    # ── strategy_buy_tag_link: создать если не существует ─────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS strategy_buy_tag_link (
            strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES buy_tags(id) ON DELETE CASCADE,
            PRIMARY KEY (strategy_id, tag_id)
        );
    """)

    # ── Seed buy_tags если пустые ──────────────────────────────────
    op.execute("""
        INSERT INTO buy_tags (name) VALUES
            ('Eco Round'), ('Full Buy'), ('Force Buy'), ('Pistol Round')
        ON CONFLICT (name) DO NOTHING;
    """)

    # ── Seed maps если пустые ─────────────────────────────────────
    op.execute("""
        INSERT INTO maps (name, is_active) VALUES
            ('Mirage', true), ('Inferno', true), ('Nuke', true),
            ('Dust2', true), ('Ancient', true), ('Anubis', true), ('Vertigo', true)
        ON CONFLICT (name) DO NOTHING;
    """)

    # ── Fix GrenadeTypeEnum: старые значения были lowercase ────────
    # Если в БД тип grenadetypeenum с lowercase значениями — пересоздаём
    op.execute("""
        DO $$
        BEGIN
            -- Добавляем новые значения если их нет
            BEGIN ALTER TYPE grenadetypeenum ADD VALUE IF NOT EXISTS 'Smoke'; EXCEPTION WHEN others THEN NULL; END;
            BEGIN ALTER TYPE grenadetypeenum ADD VALUE IF NOT EXISTS 'Flashbang'; EXCEPTION WHEN others THEN NULL; END;
            BEGIN ALTER TYPE grenadetypeenum ADD VALUE IF NOT EXISTS 'Molotov'; EXCEPTION WHEN others THEN NULL; END;
            BEGIN ALTER TYPE grenadetypeenum ADD VALUE IF NOT EXISTS 'HE'; EXCEPTION WHEN others THEN NULL; END;
            BEGIN ALTER TYPE grenadetypeenum ADD VALUE IF NOT EXISTS 'Decoy'; EXCEPTION WHEN others THEN NULL; END;
        END $$;
    """)


def downgrade() -> None:
    pass  # Non-destructive migration — no downgrade needed