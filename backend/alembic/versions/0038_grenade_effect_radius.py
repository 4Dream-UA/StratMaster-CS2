"""A per-grenade arrival radius the author sets themselves

Effect zones were removed in an earlier pass because they were hard-coded
per type and enormous — a smoke covered a fifth of the map and buried the
callouts underneath it. This brings the idea back under the author's
control: null means no circle at all (the default, and what every existing
grenade gets), and anything else is exactly the size that grenade should
show.

Revision ID: 0038_grenade_effect_radius
Revises: 0037_grenade_timing_and_bounces
Create Date: 2026-09-03 00:00:00
"""
from alembic import op

revision = "0038_grenade_effect_radius"
down_revision = "0037_grenade_timing_and_bounces"
branch_labels = None
depends_on = None

TABLES = ("grenades", "personal_board_grenades")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS effect_radius DOUBLE PRECISION;")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS effect_radius;")
