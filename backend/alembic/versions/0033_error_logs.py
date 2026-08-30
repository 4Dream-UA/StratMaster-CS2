"""Lightweight self-hosted error logging (frontend + backend)

Revision ID: 0033_error_logs
Revises: 0032_forum_post_reports
Create Date: 2026-08-31 00:00:03
"""
from alembic import op

revision = "0033_error_logs"
down_revision = "0032_forum_post_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS error_logs (
            id UUID PRIMARY KEY,
            source VARCHAR(16) NOT NULL,
            message TEXT NOT NULL,
            stack TEXT,
            url VARCHAR(512),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_error_logs_created_at ON error_logs (created_at DESC);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS error_logs;")
