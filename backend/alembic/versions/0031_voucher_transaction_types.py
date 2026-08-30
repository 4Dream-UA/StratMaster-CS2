"""Add voucher_gift / voucher_sale transaction types

Revision ID: 0031_voucher_transaction_types
Revises: 0030_premium_vouchers
Create Date: 2026-08-31 00:00:01
"""
from alembic import op

revision = "0031_voucher_transaction_types"
down_revision = "0030_premium_vouchers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            BEGIN ALTER TYPE transactiontypeenum ADD VALUE IF NOT EXISTS 'voucher_gift'; EXCEPTION WHEN others THEN NULL; END;
        END $$;
    """)
    op.execute("""
        DO $$
        BEGIN
            BEGIN ALTER TYPE transactiontypeenum ADD VALUE IF NOT EXISTS 'voucher_sale'; EXCEPTION WHEN others THEN NULL; END;
        END $$;
    """)


def downgrade() -> None:
    pass
