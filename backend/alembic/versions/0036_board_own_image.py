"""A personal board carries its own map image instead of borrowing a map's

Boards used to point at a row in `maps` and render that map's cover. That
made a board unusable whenever the chosen map had no cover uploaded yet
("ask an admin to add one"), and limited boards to the maps the catalog
happens to carry. They now hold their own image, supplied by whoever creates
the board — a URL or an upload.

Revision ID: 0036_board_own_image
Revises: 0035_ai_support_agent
Create Date: 2026-09-01 00:00:00
"""
from alembic import op

revision = "0036_board_own_image"
down_revision = "0035_ai_support_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE personal_boards ADD COLUMN IF NOT EXISTS image_url VARCHAR(512);")
    # Existing boards keep exactly the picture they were already showing.
    op.execute("""
        UPDATE personal_boards b
        SET image_url = m.cover_image_url
        FROM maps m
        WHERE m.id = b.map_id AND b.image_url IS NULL;
    """)
    # image_url is left nullable on purpose: a legacy board whose map never
    # had a cover has nothing to backfill from, and throwing away someone's
    # saved paths over a missing picture would be the wrong trade. The API
    # requires the field on create and update, so any such board gets one
    # the first time it is saved again.
    op.execute("ALTER TABLE personal_boards DROP COLUMN IF EXISTS map_id;")


def downgrade() -> None:
    # Re-added nullable: the original column was NOT NULL, but once the
    # association is gone there is no map to point these rows back at.
    op.execute(
        "ALTER TABLE personal_boards ADD COLUMN IF NOT EXISTS map_id INTEGER "
        "REFERENCES maps(id) ON DELETE CASCADE;"
    )
    op.execute("ALTER TABLE personal_boards DROP COLUMN IF EXISTS image_url;")
