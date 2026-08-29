"""Rename the seeded case to English — app is English-only

Revision ID: 0016_case_english_name
Revises: 0015_cases
Create Date: 2026-08-29 00:00:00
"""
from alembic import op

revision = "0016_case_english_name"
down_revision = "0015_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE cases SET name = 'MasterCoins Case' WHERE name = 'Основная модель';
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE cases SET name = 'Основная модель' WHERE name = 'MasterCoins Case';
    """)
