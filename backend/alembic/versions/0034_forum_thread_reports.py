"""Player-side content reporting for whole forum threads

The thread-level counterpart of 0032_forum_post_reports — same shape, keyed
on the thread instead of one post inside it.

Revision ID: 0034_forum_thread_reports
Revises: 0033_error_logs
Create Date: 2026-08-31 00:00:04
"""
from alembic import op

revision = "0034_forum_thread_reports"
down_revision = "0033_error_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS forum_thread_reports (
            id UUID PRIMARY KEY,
            thread_id UUID NOT NULL REFERENCES forum_threads(id) ON DELETE CASCADE,
            reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reason VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMP WITH TIME ZONE
        );
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_forum_thread_reports_thread "
        "ON forum_thread_reports (thread_id, resolved_at);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forum_thread_reports;")
