"""Rebalance the MasterCoins Case odds — 2 grey / 2 blue / 2 purple / 1 red,
tuned for ~80% RTP (spend 1250, expect ~1000 back on average), a step up
from the original 67% RTP table.

Revision ID: 0019_case_rebalance
Revises: 0018_board_annotations
Create Date: 2026-08-29 00:00:00
"""
import json

from alembic import op

revision = "0019_case_rebalance"
down_revision = "0018_board_annotations"
branch_labels = None
depends_on = None

NEW_REWARDS = [
    {"coins": 5, "chance_percent": 18},
    {"coins": 10, "chance_percent": 18},
    {"coins": 25, "chance_percent": 20},
    {"coins": 49, "chance_percent": 20},
    {"coins": 50, "chance_percent": 12},
    {"coins": 100, "chance_percent": 8},
    {"coins": 200, "chance_percent": 4},
]

OLD_REWARDS = [
    {"coins": 5, "chance_percent": 20},
    {"coins": 10, "chance_percent": 20},
    {"coins": 25, "chance_percent": 22},
    {"coins": 49, "chance_percent": 22},
    {"coins": 50, "chance_percent": 9},
    {"coins": 100, "chance_percent": 5},
    {"coins": 200, "chance_percent": 2},
]


def upgrade() -> None:
    op.execute(
        f"UPDATE cases SET rewards = '{json.dumps(NEW_REWARDS)}'::jsonb WHERE name = 'MasterCoins Case';"
    )


def downgrade() -> None:
    op.execute(
        f"UPDATE cases SET rewards = '{json.dumps(OLD_REWARDS)}'::jsonb WHERE name = 'MasterCoins Case';"
    )
