"""Add cases, case_openings tables + seed the "Основная модель" coin case

Revision ID: 0015_cases
Revises: 0014_auto_renew_method
Create Date: 2026-08-28 00:00:00
"""
import json
import uuid

from alembic import op

revision = "0015_cases"
down_revision = "0014_auto_renew_method"
branch_labels = None
depends_on = None

CASE_REWARDS = [
    {"coins": 5, "chance_percent": 20},
    {"coins": 10, "chance_percent": 20},
    {"coins": 25, "chance_percent": 22},
    {"coins": 49, "chance_percent": 22},
    {"coins": 50, "chance_percent": 9},
    {"coins": 100, "chance_percent": 5},
    {"coins": 200, "chance_percent": 2},
]


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            BEGIN ALTER TYPE transactiontypeenum ADD VALUE IF NOT EXISTS 'case_open'; EXCEPTION WHEN others THEN NULL; END;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id UUID PRIMARY KEY,
            name VARCHAR(64) NOT NULL,
            cost_coins INTEGER NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            rewards JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS case_openings (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            coins_spent INTEGER NOT NULL,
            coins_won INTEGER NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)

    op.execute(f"""
        INSERT INTO cases (id, name, cost_coins, is_active, rewards) VALUES
            ('{uuid.uuid4()}', 'Основная модель', 49, true, '{json.dumps(CASE_REWARDS)}'::jsonb);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS case_openings;")
    op.execute("DROP TABLE IF EXISTS cases;")
