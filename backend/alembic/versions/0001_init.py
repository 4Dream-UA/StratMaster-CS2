"""Initial migration — create all tables

Revision ID: 0001_init
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("referred_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["referred_by_id"], ["users.id"]),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    # --- wallets ---
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("wallet_id", sa.String(16), nullable=False),
        sa.Column("balance_coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ref_discount_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("wallet_id"),
    )
    op.create_index("ix_wallets_wallet_id", "wallets", ["wallet_id"], unique=True)

    # --- transactions ---
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_wallet_id", sa.String(16), nullable=True),
        sa.Column("receiver_wallet_id", sa.String(16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column(
            "transaction_type",
            sa.Enum(
                "p2p_transfer", "subscription_buy", "crypto_deposit",
                "referral_bonus", "promo_code",
                name="transactiontype",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- promo_codes ---
    op.create_table(
        "promo_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("coin_reward", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("activations_limit", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promo_codes_code", "promo_codes", ["code"], unique=True)

    # --- maps ---
    op.create_table(
        "maps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("cover_image_url", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # --- strategies ---
    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("map_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("side", sa.Enum("T_side", "CT_side", name="sideenum"), nullable=False),
        sa.Column("plant", sa.Enum("A", "B", name="plantenum"), nullable=False),
        sa.Column("speed", sa.Enum("fast", "medium", "slow", name="speedenum"), nullable=False),
        sa.Column("difficulty_stars", sa.Integer(), nullable=False),
        sa.Column("success_rate", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(128), nullable=True),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("roles_description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["map_id"], ["maps.id"]),
    )

    # --- grenades ---
    op.create_table(
        "grenades",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "grenade_type",
            sa.Enum("smoke", "flash", "molotov", "he", "decoy", name="grenadetypeenum"),
            nullable=False,
        ),
        sa.Column("destination", sa.String(128), nullable=False),
        sa.Column("timing", sa.String(32), nullable=True),
        sa.Column("lineup_url", sa.String(512), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"]),
    )

    # --- strategy_images ---
    op.create_table(
        "strategy_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(512), nullable=False),
        sa.Column("is_main", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"]),
    )

    # --- Seed maps ---
    op.execute("""
        INSERT INTO maps (name, is_active) VALUES
        ('Mirage', true), ('Inferno', true), ('Nuke', true),
        ('Dust2', true), ('Ancient', true), ('Anubis', true), ('Vertigo', true)
    """)


def downgrade() -> None:
    op.drop_table("strategy_images")
    op.drop_table("grenades")
    op.drop_table("strategies")
    op.drop_table("maps")
    op.drop_table("promo_codes")
    op.drop_table("transactions")
    op.drop_table("wallets")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS sideenum")
    op.execute("DROP TYPE IF EXISTS plantenum")
    op.execute("DROP TYPE IF EXISTS speedenum")
    op.execute("DROP TYPE IF EXISTS grenadetypeenum")