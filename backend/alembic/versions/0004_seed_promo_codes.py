from alembic import op

revision = "0004_seed_promo_codes"
down_revision = "0003_fix_strategies_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO promo_codes (id, code, coin_reward, is_active, activations_limit, used_count)
        VALUES
            (gen_random_uuid(), 'WELCOME25', 25, true, 1000, 0),
            (gen_random_uuid(), 'INVESTOR50', 50, true, 50, 0)
        ON CONFLICT (code) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DELETE FROM promo_codes WHERE code IN ('WELCOME25', 'INVESTOR50');")
