"""Rebalance MasterCoins Case, add Mega Master Coin Case and Premium Case

All three tuned for the same ~80% RTP target as the shared case-economy
instrument (backend/app/services/case_economy.py) assumes: spend 1250,
expect ~1000 back on average, coin-equivalent for the Premium Case's
subscription-day tiers.

Revision ID: 0027_case_economy_rebalance
Revises: 0026_case_economy_ledger
Create Date: 2026-08-30 00:00:00
"""
import json
import uuid

from alembic import op

revision = "0027_case_economy_rebalance"
down_revision = "0026_case_economy_ledger"
branch_labels = None
depends_on = None

# EV = 39.225 on a 49-cost case → RTP 80.05%
MASTERCOINS_REWARDS = [
    {"coins": 5, "chance_percent": 18.5, "tier": "grey"},
    {"coins": 10, "chance_percent": 18, "tier": "grey"},
    {"coins": 25, "chance_percent": 22, "tier": "blue"},
    {"coins": 50, "chance_percent": 20, "tier": "blue"},
    {"coins": 75, "chance_percent": 12, "tier": "purple"},
    {"coins": 100, "chance_percent": 7, "tier": "purple"},
    {"coins": 200, "chance_percent": 2.5, "tier": "red"},
]

OLD_MASTERCOINS_REWARDS = [
    {"coins": 5, "chance_percent": 18},
    {"coins": 10, "chance_percent": 18},
    {"coins": 25, "chance_percent": 20},
    {"coins": 49, "chance_percent": 20},
    {"coins": 50, "chance_percent": 12},
    {"coins": 100, "chance_percent": 8},
    {"coins": 200, "chance_percent": 4},
]

# EV = 159.1 on a 199-cost case → RTP 79.95%
MEGA_REWARDS = [
    {"coins": 50, "chance_percent": 23.8, "tier": "grey"},
    {"coins": 100, "chance_percent": 21, "tier": "grey"},
    {"coins": 150, "chance_percent": 18, "tier": "blue"},
    {"coins": 200, "chance_percent": 15, "tier": "blue"},
    {"coins": 250, "chance_percent": 11, "tier": "purple"},
    {"coins": 300, "chance_percent": 6, "tier": "purple"},
    {"coins": 400, "chance_percent": 3.2, "tier": "red"},
    {"coins": 500, "chance_percent": 1.7, "tier": "red"},
    {"coins": 800, "chance_percent": 0.3, "tier": "legendary"},
]

# EV = 79.15 coin-equivalent on a 99-cost case → RTP 79.9%. Days, not
# months, since grant_premium_days() takes days directly (30-day months).
PREMIUM_REWARDS = [
    {"premium_days": 0, "chance_percent": 28, "tier": "grey"},
    {"premium_days": 7, "chance_percent": 24, "tier": "grey"},
    {"premium_days": 14, "chance_percent": 20, "tier": "blue"},
    {"premium_days": 31, "chance_percent": 15, "tier": "blue"},
    {"premium_days": 90, "chance_percent": 8.5, "tier": "purple"},
    {"premium_days": 180, "chance_percent": 3.5, "tier": "purple"},
    {"premium_days": 360, "chance_percent": 1, "tier": "red"},
]


def upgrade() -> None:
    op.execute(
        f"UPDATE cases SET rewards = '{json.dumps(MASTERCOINS_REWARDS)}'::jsonb WHERE name = 'MasterCoins Case';"
    )
    op.execute(f"""
        INSERT INTO cases (id, name, cost_coins, is_active, rewards) VALUES
            ('{uuid.uuid4()}', 'Mega Master Coin Case', 199, true, '{json.dumps(MEGA_REWARDS)}'::jsonb);
    """)
    op.execute(f"""
        INSERT INTO cases (id, name, cost_coins, is_active, rewards) VALUES
            ('{uuid.uuid4()}', 'Premium Case', 99, true, '{json.dumps(PREMIUM_REWARDS)}'::jsonb);
    """)


def downgrade() -> None:
    op.execute("DELETE FROM cases WHERE name = 'Premium Case';")
    op.execute("DELETE FROM cases WHERE name = 'Mega Master Coin Case';")
    op.execute(
        f"UPDATE cases SET rewards = '{json.dumps(OLD_MASTERCOINS_REWARDS)}'::jsonb WHERE name = 'MasterCoins Case';"
    )
