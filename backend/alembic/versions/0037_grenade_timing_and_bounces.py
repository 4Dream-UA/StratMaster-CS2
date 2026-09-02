"""Grenades get their own throw/land times and a multi-point trajectory

Playback used to derive a grenade's timing from the free-text `timing` label
and fly it along a fixed parabola between exactly two points. That can't
express a bounce off a wall, and it can't say "thrown at 0:08, lands at
0:11" — the flight was always the same 1.2s.

Both new time columns are nullable: a grenade without them still falls back
to parsing `timing`, so nothing already authored changes behaviour. Same for
`trajectory` — null means "use from_/to_ as before".

The C4's plant time lives in the annotations JSONB and needs no column.

Revision ID: 0037_grenade_timing_and_bounces
Revises: 0036_board_own_image
Create Date: 2026-09-02 00:00:00
"""
from alembic import op

revision = "0037_grenade_timing_and_bounces"
down_revision = "0036_board_own_image"
branch_labels = None
depends_on = None

TABLES = ("grenades", "personal_board_grenades")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS throw_at DOUBLE PRECISION;")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS lands_at DOUBLE PRECISION;")
        # [{"x": 12.5, "y": 80.1}, ...] — two or more points, so a throw can
        # bank off geometry instead of arcing straight to the target.
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS trajectory JSONB;")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS trajectory;")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS lands_at;")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS throw_at;")
