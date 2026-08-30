"""Player-side content reporting for forum posts

Revision ID: 0032_forum_post_reports
Revises: 0031_voucher_transaction_types
Create Date: 2026-08-31 00:00:02
"""
from alembic import op

revision = "0032_forum_post_reports"
down_revision = "0031_voucher_transaction_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_post_reports (
            id UUID PRIMARY KEY,
            post_id UUID NOT NULL REFERENCES forum_posts(id) ON DELETE CASCADE,
            reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reason VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_forum_post_reports_post ON forum_post_reports (post_id, resolved_at);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forum_post_reports;")
