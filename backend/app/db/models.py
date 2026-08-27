import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Column,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.database import Base


# ─────────────────────────────────────────────
#  Enums
# ─────────────────────────────────────────────

class SideEnum(str, enum.Enum):
    T_side = "T_side"
    CT_side = "CT_side"


class PlantEnum(str, enum.Enum):
    A = "A"
    B = "B"


class SpeedEnum(str, enum.Enum):
    fast = "fast"      # < 40 sec
    medium = "medium"  # 40–80 sec
    slow = "slow"      # > 80 sec


class GrenadeTypeEnum(str, enum.Enum):
    Smoke = "Smoke"
    Flashbang = "Flashbang"
    Molotov = "Molotov"
    HE = "HE"
    Decoy = "Decoy"


class TransactionTypeEnum(str, enum.Enum):
    p2p_transfer = "p2p_transfer"
    subscription_buy = "subscription_buy"
    crypto_deposit = "crypto_deposit"
    referral_bonus = "referral_bonus"
    promo_code = "promo_code"


# ─────────────────────────────────────────────
#  Many-to-Many: Strategy <-> BuyTag
# ─────────────────────────────────────────────

strategy_buy_tag_link = Table(
    "strategy_buy_tag_link",
    Base.metadata,
    Column("strategy_id", UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("buy_tags.id", ondelete="CASCADE"), primary_key=True),
)


# ─────────────────────────────────────────────
#  User App Models
# ─────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referred_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    wallet: Mapped["WalletModel"] = relationship("WalletModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    referred_by: Mapped["UserModel | None"] = relationship("UserModel", remote_side="UserModel.id", foreign_keys=[referred_by_id])


class WalletModel(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    wallet_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    balance_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ref_discount_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # True once the lifetime plan has been purchased — distinguishes "paid
    # once, forever" from an ordinary (very long) premium subscription so the
    # shop and reminder job can treat it as never expiring.
    is_lifetime: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Duration (in months) of the last premium purchase — reused by the
    # "renew" action so it charges the same plan the user already had.
    last_plan_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Opt-in: auto-charge MasterCoins to renew when the subscription is
    # about to expire (the bot reminder still always fires 24h out).
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # The subscription_expires_at value the 24h-expiry reminder was last
    # sent for — compared against the current value so each renewal cycle
    # gets its own reminder instead of firing once, ever.
    reminder_sent_for_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="wallet")


class TransactionModel(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_wallet_id: Mapped[str | None] = mapped_column(String(16), nullable=True)   # Null = system grant
    receiver_wallet_id: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[TransactionTypeEnum] = mapped_column(
        Enum(TransactionTypeEnum), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CryptoInvoiceModel(Base):
    """A CryptoPay invoice we created, tracked so the signed webhook can be
    matched back to who's paying for what — and so a retried webhook can be
    recognized as already-processed instead of double-crediting the wallet.
    """
    __tablename__ = "crypto_invoices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # MasterCoins this invoice will credit once paid — every crypto payment
    # tops up coins at the fixed $0.01/coin rate first, matching the ТЗ
    # requirement that MasterCoins themselves be purchasable via crypto.
    coins: Mapped[int] = mapped_column(Integer, nullable=False)
    # If set, the credited coins are immediately spent on this plan once
    # paid (a "pay with crypto" checkout) — a null plan means a plain
    # coin top-up with no auto-purchase.
    plan: Mapped[str | None] = mapped_column(String(16), nullable=True)
    months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount_usd: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)  # active | paid | expired
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel")


class PromoCodeModel(Base):
    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    coin_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activations_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class PromoRedemptionModel(Base):
    """Tracks which user redeemed which promo code — enforces one redemption per user per code."""
    __tablename__ = "promo_redemptions"
    __table_args__ = (
        UniqueConstraint("user_id", "promo_code_id", name="uq_promo_redemption_user_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="CASCADE"), nullable=False
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FavoriteMapModel(Base):
    """A user's pinned map — powers the "Favorite Maps" panel and, later,
    bot notifications for new strategies on a followed map."""
    __tablename__ = "favorite_maps"
    __table_args__ = (
        UniqueConstraint("user_id", "map_id", name="uq_favorite_user_map"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    map_id: Mapped[int] = mapped_column(Integer, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    map: Mapped["MapModel"] = relationship("MapModel")


# ─────────────────────────────────────────────
#  Strategy App Models
# ─────────────────────────────────────────────

class MapModel(Base):
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    cover_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationship
    strategies: Mapped[list["StrategyModel"]] = relationship("StrategyModel", back_populates="map")


class BuyTagModel(Base):
    __tablename__ = "buy_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # "Eco Round", "Full Buy", etc.

    # Relationship
    strategies: Mapped[list["StrategyModel"]] = relationship(
        "StrategyModel", secondary=strategy_buy_tag_link, back_populates="buy_tags"
    )


class StrategyModel(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    map_id: Mapped[int] = mapped_column(Integer, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    side: Mapped[SideEnum] = mapped_column(Enum(SideEnum), nullable=False)
    plant: Mapped[PlantEnum] = mapped_column(Enum(PlantEnum), nullable=False)
    speed: Mapped[SpeedEnum] = mapped_column(Enum(SpeedEnum), nullable=False)
    difficulty_stars: Mapped[int] = mapped_column(Integer, nullable=False, default=3)  # 1–5
    success_rate: Mapped[int] = mapped_column(Integer, nullable=False, default=75)     # 1–100
    author: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_free: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timings_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    map: Mapped["MapModel"] = relationship("MapModel", back_populates="strategies")
    buy_tags: Mapped[list["BuyTagModel"]] = relationship(
        "BuyTagModel", secondary=strategy_buy_tag_link, back_populates="strategies"
    )
    images: Mapped[list["ImageModel"]] = relationship(
        "ImageModel", back_populates="strategy", cascade="all, delete-orphan", order_by="ImageModel.order"
    )
    grenades: Mapped[list["GrenadeModel"]] = relationship(
        "GrenadeModel", back_populates="strategy", cascade="all, delete-orphan", order_by="GrenadeModel.order"
    )
    player_paths: Mapped[list["PlayerPathModel"]] = relationship(
        "PlayerPathModel", back_populates="strategy", cascade="all, delete-orphan", order_by="PlayerPathModel.order"
    )


class ImageModel(Base):
    __tablename__ = "images"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationship
    strategy: Mapped["StrategyModel"] = relationship("StrategyModel", back_populates="images")


class GrenadeModel(Base):
    __tablename__ = "grenades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    grenade_type: Mapped[GrenadeTypeEnum] = mapped_column(Enum(GrenadeTypeEnum), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    timing: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. "0:08"
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Throw → landing spot, as a % of the main map image's width/height
    # (0-100) so the tactics player can position it regardless of the
    # image's actual pixel size. Null on either end = no animated
    # trajectory for this grenade (falls back to the plain text card).
    from_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    from_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    to_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    to_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationship
    strategy: Mapped["StrategyModel"] = relationship("StrategyModel", back_populates="grenades")


class PlayerPathModel(Base):
    """A single player's movement — a sequence of {x, y, t} waypoints
    (percent-of-image coordinates, seconds-from-round-start) that the
    tactics player animates a colored dot along."""
    __tablename__ = "player_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "Entry", "AWP"
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#ff9a00")
    waypoints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{"x":.., "y":.., "t":..}, ...]
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    strategy: Mapped["StrategyModel"] = relationship("StrategyModel", back_populates="player_paths")


class FavoriteStrategyModel(Base):
    """A user's bookmarked strategy — separate from FavoriteMapModel: you
    might like everything on Dust2, but only want to pin one specific
    execute you're planning to run tonight."""
    __tablename__ = "favorite_strategies"
    __table_args__ = (
        UniqueConstraint("user_id", "strategy_id", name="uq_favorite_user_strategy"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    strategy: Mapped["StrategyModel"] = relationship("StrategyModel")