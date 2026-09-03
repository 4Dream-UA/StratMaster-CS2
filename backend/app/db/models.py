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
    case_open = "case_open"
    case_gift = "case_gift"
    case_sale = "case_sale"
    admin_grant = "admin_grant"
    voucher_gift = "voucher_gift"
    voucher_sale = "voucher_sale"


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
    # Player-chosen display name — shown big/primary everywhere, with the
    # Telegram @username as a small secondary line. Falls back to username
    # (or telegram_id) when unset.
    display_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # The AI support assistant posts as a real user row (forum_posts.user_id
    # is NOT NULL) — this is what tells it apart from a player, so the forum
    # can label its messages rather than passing them off as a human's.
    is_ai_agent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # Full account ban — enforced in get_current_user, locks every endpoint.
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Lighter than is_banned: still full app access, just can't send P2P
    # transfers/case gifts/case sales to anyone.
    is_trade_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referred_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Hides the @username line on forum posts/threads from other players
    # (admins always see it — needed for moderation). Display name, if set,
    # still shows; this only affects the Telegram handle.
    hide_username_on_forum: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # Optional, player-filled contact/social info shown on their public
    # profile popup — every key optional, e.g. {"location": "...",
    # "telegram": "...", "steam": "...", "discord": "...", ...}. Filling
    # a field in is the opt-in; there's no separate visibility toggle.
    profile_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
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
    # "mastercoins" | "crypto" — which payment method auto-renew uses. Crypto
    # can't actually be auto-charged (no pull payments), so that path instead
    # has the 24h reminder pre-generate a ready-to-pay invoice; see
    # subscription_reminders.py.
    auto_renew_method: Mapped[str] = mapped_column(String(16), default="mastercoins", nullable=False)
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

    # "coins" (default/legacy) | "premium" | "case"
    reward_type: Mapped[str] = mapped_column(String(16), default="coins", server_default="coins", nullable=False)
    # Used when reward_type == "premium". 0 means lifetime/forever.
    premium_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Used when reward_type == "case".
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True
    )
    case_quantity: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)

    case: Mapped["CaseModel | None"] = relationship("CaseModel")


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
    # Freeform overlay: arbitrary drawn lines, text notes, one C4 marker —
    # see backend/app/schemas/annotations.py for the shape.
    annotations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
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

    # When it leaves the hand and when it arrives, in seconds from round
    # start. Null falls back to parsing the free-text `timing` label with a
    # fixed flight time, which is how every grenade authored before 0037
    # still plays.
    throw_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    lands_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    # [{"x": .., "y": ..}, ...] — two or more points, so a throw can bank
    # off a wall instead of arcing straight at the target. Null means use
    # from_/to_ as a single arc.
    trajectory: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Radius of the circle drawn where it lands, as a percent of the image.
    # Null = draw none, which is the default: a hard-coded per-type radius
    # was tried once and covered a fifth of the map.
    effect_radius: Mapped[float | None] = mapped_column(Float, nullable=True)

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


personal_board_collaborator_link = Table(
    "personal_board_collaborator_link",
    Base.metadata,
    Column("board_id", UUID(as_uuid=True), ForeignKey("personal_boards.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class PersonalBoardModel(Base):
    """A premium user's private tactics board — the same player-paths +
    grenade-trajectories building blocks as an admin-authored strategy, but
    owned by one user, never published, and editable only by them (plus
    whoever they've explicitly added as a collaborator). Lets a subscriber
    sketch their own executes on any map, separate from the official
    strategy catalog."""
    __tablename__ = "personal_boards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # The board's own backdrop — a URL the creator supplied or uploaded,
    # rather than a row in `maps`. Nullable only for boards created before
    # 0036 whose map had no cover to backfill from; the API requires it.
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    # Set only once the owner taps "Copy public link" — null means no public
    # link has ever been generated (or it was revoked by clearing this).
    share_token: Mapped[str | None] = mapped_column(String(24), unique=True, nullable=True)
    # Freeform overlay: arbitrary drawn lines, text notes, one C4 marker —
    # see backend/app/schemas/annotations.py for the shape.
    annotations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    paths: Mapped[list["PersonalBoardPathModel"]] = relationship(
        "PersonalBoardPathModel", back_populates="board", cascade="all, delete-orphan", order_by="PersonalBoardPathModel.order"
    )
    grenades: Mapped[list["PersonalBoardGrenadeModel"]] = relationship(
        "PersonalBoardGrenadeModel", back_populates="board", cascade="all, delete-orphan", order_by="PersonalBoardGrenadeModel.order"
    )
    collaborators: Mapped[list["UserModel"]] = relationship(
        "UserModel", secondary=personal_board_collaborator_link
    )


class PersonalBoardPathModel(Base):
    __tablename__ = "personal_board_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personal_boards.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#ff9a00")
    waypoints: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    board: Mapped["PersonalBoardModel"] = relationship("PersonalBoardModel", back_populates="paths")


class PersonalBoardGrenadeModel(Base):
    __tablename__ = "personal_board_grenades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("personal_boards.id", ondelete="CASCADE"), nullable=False
    )
    grenade_type: Mapped[GrenadeTypeEnum] = mapped_column(Enum(GrenadeTypeEnum), nullable=False)
    target: Mapped[str] = mapped_column(String(64), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    from_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    from_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    to_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    to_y: Mapped[float | None] = mapped_column(Float, nullable=True)

    # When it leaves the hand and when it arrives, in seconds from round
    # start. Null falls back to parsing the free-text `timing` label with a
    # fixed flight time, which is how every grenade authored before 0037
    # still plays.
    throw_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    lands_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    # [{"x": .., "y": ..}, ...] — two or more points, so a throw can bank
    # off a wall instead of arcing straight at the target. Null means use
    # from_/to_ as a single arc.
    trajectory: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Radius of the circle drawn where it lands, as a percent of the image.
    # Null = draw none, which is the default: a hard-coded per-type radius
    # was tried once and covered a fifth of the map.
    effect_radius: Mapped[float | None] = mapped_column(Float, nullable=True)

    board: Mapped["PersonalBoardModel"] = relationship("PersonalBoardModel", back_populates="grenades")


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


# ─────────────────────────────────────────────
#  Cases (lootboxes) — coins-in, weighted-random coins-out
# ─────────────────────────────────────────────

class CaseModel(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_coins: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # [{"coins": 5, "chance_percent": 20}, ...] — chance_percent across all
    # entries must sum to 100; enforced at seed/admin-edit time, not by the DB.
    rewards: Mapped[list] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CaseOpeningModel(Base):
    """One case-open event — kept as a permanent history/audit trail, not
    just for the transaction ledger, so a player (or support) can see
    exactly what a given case paid out and when."""
    __tablename__ = "case_openings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    coins_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    coins_won: Mapped[int] = mapped_column(Integer, nullable=False)
    # Set (not None) exactly when this opening resolved to a premium-days
    # tier instead of a coins tier — 0 unambiguously means "nothing" for a
    # premium case, since coins_won already covers the coins case's 0-ish
    # outcomes and no premium tier is ever literally 0 days-but-a-win.
    premium_days_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case: Mapped["CaseModel"] = relationship("CaseModel")


class CaseInventoryModel(Base):
    """One purchased-but-not-yet-opened case. Buying a case inserts a row
    here; opening it (alone or in an x2/x5 batch) deletes the row and
    resolves a CaseOpeningModel for it — buy and open are now two separate
    actions instead of one atomic pay-and-reveal."""
    __tablename__ = "case_inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    case: Mapped["CaseModel"] = relationship("CaseModel")


# ─────────────────────────────────────────────
#  Forum — premium-only. Two categories seeded by migration: "lounge"
#  (open discussion, any premium user can start/reply to any thread) and
#  "support" (each non-admin user gets exactly one private thread, visible
#  only to them and admins — a ticket, not a public board).
# ─────────────────────────────────────────────

class ForumCategoryModel(Base):
    __tablename__ = "forum_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # "lounge" | "support"
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=False)


class ForumThreadModel(Base):
    __tablename__ = "forum_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_categories.id", ondelete="CASCADE"), nullable=False
    )
    # The thread starter — for "support" this is also who the ticket is
    # scoped to (only them + admins can see it).
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Closed = admin marked it resolved (mainly for support tickets) — no
    # more replies from non-admins, but still viewable.
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_token: Mapped[str | None] = mapped_column(String(24), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category: Mapped["ForumCategoryModel"] = relationship("ForumCategoryModel")
    user: Mapped["UserModel"] = relationship("UserModel")
    posts: Mapped[list["ForumPostModel"]] = relationship(
        "ForumPostModel", back_populates="thread", cascade="all, delete-orphan", order_by="ForumPostModel.created_at"
    )
    reports: Mapped[list["ForumThreadReportModel"]] = relationship(
        "ForumThreadReportModel", back_populates="thread", cascade="all, delete-orphan"
    )


class ForumThreadWatcherModel(Base):
    """One row = one user watching one thread — auto-added when you start a
    thread or post in it, toggleable explicitly otherwise. Drives the
    Telegram notification on new replies."""
    __tablename__ = "forum_thread_watchers"
    __table_args__ = (UniqueConstraint("thread_id", "user_id", name="uq_forum_thread_watcher"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class ForumPostModel(Base):
    __tablename__ = "forum_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # A reply can quote/target one specific earlier post in the same thread.
    # SET NULL on delete — losing the quoted post shouldn't delete this reply.
    reply_to_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_posts.id", ondelete="SET NULL"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Set together whenever body changes after creation. edited_by_id lets
    # the UI flag "edited by an admin" distinctly from the author editing
    # their own message — the full before/after is in ForumPostEditModel.
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Soft delete: the author (or an admin) can delete their own message,
    # but the row and its body are kept around — hidden from regular
    # players, still visible (with a "deleted" marker) to admins, who can
    # restore it or permanently erase it.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Whisper/private reply: null/empty means visible to the whole thread
    # (the normal case). A non-empty list of user-id strings restricts
    # visibility to just those players — plus the author and any admin,
    # who can always see everything.
    visible_to_user_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)

    thread: Mapped["ForumThreadModel"] = relationship("ForumThreadModel", back_populates="posts")
    user: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[user_id])
    reply_to: Mapped["ForumPostModel | None"] = relationship("ForumPostModel", remote_side=[id])
    reactions: Mapped[list["ForumPostReactionModel"]] = relationship(
        "ForumPostReactionModel", cascade="all, delete-orphan"
    )
    edits: Mapped[list["ForumPostEditModel"]] = relationship(
        "ForumPostEditModel", cascade="all, delete-orphan", order_by="ForumPostEditModel.edited_at.desc()"
    )
    reports: Mapped[list["ForumPostReportModel"]] = relationship(
        "ForumPostReportModel", back_populates="post", cascade="all, delete-orphan",
        order_by="ForumPostReportModel.created_at.desc()"
    )


class ForumPostEditModel(Base):
    """One row per edit, storing the body as it was BEFORE that edit —
    lets admins see the full revision history of any message, including
    who made each change."""
    __tablename__ = "forum_post_edits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False
    )
    editor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    previous_body: Mapped[str] = mapped_column(Text, nullable=False)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    editor: Mapped["UserModel | None"] = relationship("UserModel")


class ForumPostReportModel(Base):
    """A player flagging one post for admin review — separate from
    deletion: reporting doesn't hide anything, it just surfaces the post
    to admins (as a count on the post, visible only to them) until an
    admin dismisses it."""
    __tablename__ = "forum_post_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reporter: Mapped["UserModel"] = relationship("UserModel")
    # Read-only side of the ForumPostModel.reports collection — the admin
    # moderation queue walks from the report to the post it flags, which is
    # the opposite direction from the in-thread flag badge.
    post: Mapped["ForumPostModel"] = relationship("ForumPostModel", back_populates="reports")


class ForumThreadReportModel(Base):
    """The thread-level counterpart of ForumPostReportModel — reporting a
    whole thread (its topic, its title) rather than one message inside it.
    Kept as its own table rather than a nullable post_id on the post one so
    neither foreign key has to be optional."""
    __tablename__ = "forum_thread_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_threads.id", ondelete="CASCADE"), nullable=False
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reporter: Mapped["UserModel"] = relationship("UserModel")
    # Other side of ForumThreadModel.reports — the admin moderation queue
    # walks report → thread, the opposite direction from the flag badge.
    thread: Mapped["ForumThreadModel"] = relationship("ForumThreadModel", back_populates="reports")


# A curated palette a player can react to a post with — a user may react
# with several different emoji on the same post, but only once each
# (toggling re-sends the same emoji to remove it).
REACTION_EMOJIS = ("❤️", "👍", "👎", "😂", "🤡", "🔥", "🎉", "😮", "😢", "💯", "🙏", "👀", "💀")


class ForumPostReactionModel(Base):
    __tablename__ = "forum_post_reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id", "emoji", name="uq_post_reaction"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("forum_posts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    emoji: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel")


class ErrorLogModel(Base):
    """Lightweight, self-hosted error visibility: unhandled backend
    exceptions log here automatically (see main_api.py's exception
    handler), and the frontend posts its own uncaught errors /
    rejections to POST /api/errors. Not a replacement for a real APM
    tool at scale, but closes the "a production failure is invisible
    unless a player happens to report it" gap without an external
    signup."""
    __tablename__ = "error_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # "frontend" | "backend"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["UserModel | None"] = relationship("UserModel")


# ─────────────────────────────────────────────
#  App settings — a single-row table (id is always 1) for admin-editable
#  global config that isn't tied to any one user, like the site logo.
# ─────────────────────────────────────────────

class AppSettingsModel(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Running ledger for the shared case-economy throttle (see
    # backend/app/services/case_economy.py) — coin-equivalent totals across
    # every case type, not per-case, so one case running hot can be reined
    # in by the aggregate picture just as easily as by its own history.
    case_total_spent_coins: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    case_total_paid_coins: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    # Admin kill switch for the AI support assistant — a bad answer needs to
    # be stoppable in one click, not a redeploy.
    ai_agent_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


# ─────────────────────────────────────────────
#  Trade blocking — a user can stop a specific other user from sending
#  them P2P transfers / case gifts / case sale offers; admin can do the
#  same thing app-wide via UserModel.is_trade_banned.
# ─────────────────────────────────────────────

class WalletTradeBlockModel(Base):
    __tablename__ = "wallet_trade_blocks"
    __table_args__ = (UniqueConstraint("blocker_user_id", "blocked_user_id", name="uq_trade_block"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # blocker doesn't want to receive anything from blocked.
    blocker_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    blocked_user: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[blocked_user_id])


# ─────────────────────────────────────────────
#  Case gifting + P2P case sales — one pending "offer" row per gift/sale.
#  Cases leave the sender's inventory into escrow (this row) the moment
#  the offer is created; they only land in the receiver's inventory once
#  the receiver explicitly accepts, per spec ("получатель должен
#  подтвердить подарок").
# ─────────────────────────────────────────────

class CaseOfferModel(Base):
    __tablename__ = "case_offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    receiver_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_coins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0 = gift
    offer_type: Mapped[str] = mapped_column(String(8), nullable=False)  # "gift" | "sale"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|accepted|declined|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped["CaseModel"] = relationship("CaseModel")
    sender: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[sender_user_id])
    receiver: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[receiver_user_id])


class PremiumVoucherModel(Base):
    """A premium-days case reward, landed as an inventory item instead of
    being applied to the wallet the instant it's won — the player chooses
    when (or whether) to activate it, and can gift or sell it meanwhile."""
    __tablename__ = "premium_vouchers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel")


class PremiumVoucherOfferModel(Base):
    """A pending sale of one premium voucher — gifting a voucher is instant
    (no accept step, see /cases/vouchers/{id}/gift), but a sale needs the
    buyer to actually agree to pay, so it goes through the same
    escrow-then-accept shape as a case sale offer."""
    __tablename__ = "premium_voucher_offers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    receiver_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_coins: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|accepted|declined|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sender: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[sender_user_id])
    receiver: Mapped["UserModel"] = relationship("UserModel", foreign_keys=[receiver_user_id])