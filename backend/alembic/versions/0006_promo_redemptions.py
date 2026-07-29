from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_promo_redemptions"
down_revision = "0005_fix_transaction_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS promo_redemptions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            promo_code_id UUID NOT NULL REFERENCES promo_codes(id) ON DELETE CASCADE,
            redeemed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_promo_redemption_user_code UNIQUE (user_id, promo_code_id)
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS promo_redemptions;")