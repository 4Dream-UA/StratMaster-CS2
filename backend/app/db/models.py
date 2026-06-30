import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Column,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
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


class PromoCodeModel(Base):
    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    coin_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    activations_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


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

    # Relationship
    strategy: Mapped["StrategyModel"] = relationship("StrategyModel", back_populates="grenades")