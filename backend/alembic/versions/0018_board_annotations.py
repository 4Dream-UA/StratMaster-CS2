"""Add annotations JSONB to strategies + personal_boards

Freeform overlay: arbitrary drawn lines, text notes, one C4 marker — on top
of the existing structured player-paths/grenade-trajectories.

Revision ID: 0018_board_annotations
Revises: 0017_forum
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0018_board_annotations"
down_revision = "0017_forum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE strategies ADD COLUMN IF NOT EXISTS annotations JSONB NOT NULL DEFAULT '{}'::jsonb;")
    op.execute("ALTER TABLE personal_boards ADD COLUMN IF NOT EXISTS annotations JSONB NOT NULL DEFAULT '{}'::jsonb;")


def downgrade() -> None:
    op.execute("ALTER TABLE strategies DROP COLUMN IF EXISTS annotations;")
    op.execute("ALTER TABLE personal_boards DROP COLUMN IF EXISTS annotations;")
