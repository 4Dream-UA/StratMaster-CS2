"""Rename transactiontype enum to transactiontypeenum to match current model

Revision ID: 0005_fix_transaction_enum
Revises: 0004_seed_promo_codes
Create Date: 2024-01-05 00:00:00
"""
from alembic import op

revision = "0005_fix_transaction_enum"
down_revision = "0004_seed_promo_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The very first migration created this enum type as "transactiontype"
    # (no "enum" suffix). The current SQLAlchemy model (TransactionTypeEnum)
    # auto-derives the Postgres type name as "transactiontypeenum", so every
    # insert/select touching transactions.transaction_type has been failing
    # with UndefinedObjectError. Rename the type to match.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'transactiontype'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'transactiontypeenum'
            ) THEN
                ALTER TYPE transactiontype RENAME TO transactiontypeenum;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'transactiontypeenum'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'transactiontype'
            ) THEN
                ALTER TYPE transactiontypeenum RENAME TO transactiontype;
            END IF;
        END $$;
    """)