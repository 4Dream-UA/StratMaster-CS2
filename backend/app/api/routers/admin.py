import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import AdminUser, DBSession
from backend.app.db.models import (
    BuyTagModel,
    CaseModel,
    ForumPostModel,
    ForumThreadModel,
    GrenadeModel,
    ImageModel,
    MapModel,
    PlayerPathModel,
    PromoCodeModel,
    StrategyModel,
    TransactionModel,
    UserModel,
    WalletModel,
)
from backend.app.schemas.forum import (
    AdminReportOut,
    AdminReportsListResponse,
    AdminTicketOut,
    AdminTicketsListResponse,
    ReporterOut,
)
from backend.app.schemas.strategy import (
    AdminStrategiesListResponse,
    MapCreate,
    MapResponse,
    MapsListResponse,
    MapUpdate,
    PromoCodeCreate,
    PromoCodeOut,
    PromoCodesListResponse,
    PromoCodeToggle,
    StrategyCreate,
    StrategyDetailResponse,
    StrategyUpdate,
)
from backend.app.schemas.user import (
    AdminGrantCoinsRequest,
    AdminGrantSubscriptionRequest,
    AdminSetPremiumRequest,
    SetAdminRequest,
    SetBannedRequest,
    SetNicknameRequest,
    SetTradeBannedRequest,
    UpdateAvatarRequest,
    UserAdminOut,
    UsersListResponse,
)
from backend.app.schemas.wallet import TransactionsListResponse
from backend.app.services.notifications import notify_favorited_map_users
from backend.app.services.referral import generate_promo_code
from backend.app.services.subscription import LIFETIME_YEARS, extend_subscription

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/admin/stats")
async def get_admin_stats(db: DBSession, admin_user: AdminUser) -> dict:
    """High-level counts for the admin dashboard tiles."""
    users_count = (await db.execute(select(func.count()).select_from(UserModel))).scalar() or 0
    strategies_count = (await db.execute(select(func.count()).select_from(StrategyModel))).scalar() or 0
    maps_count = (await db.execute(select(func.count()).select_from(MapModel))).scalar() or 0
    transactions_count = (await db.execute(select(func.count()).select_from(TransactionModel))).scalar() or 0

    now = datetime.now(timezone.utc)
    active_subscriptions_count = (
        await db.execute(
            select(func.count()).select_from(WalletModel).where(
                or_(WalletModel.is_lifetime.is_(True), WalletModel.subscription_expires_at > now)
            )
        )
    ).scalar() or 0

    from backend.app.db.models import (
        ErrorLogModel,
        ForumCategoryModel,
        ForumPostReportModel,
        ForumThreadReportModel,
    )

    open_tickets_count = (
        await db.execute(
            select(func.count()).select_from(ForumThreadModel)
            .join(ForumCategoryModel, ForumThreadModel.category_id == ForumCategoryModel.id)
            .where(ForumCategoryModel.key == "support", ForumThreadModel.is_closed.is_(False))
        )
    ).scalar() or 0
    pending_deleted_posts_count = (
        await db.execute(select(func.count()).select_from(ForumPostModel).where(ForumPostModel.deleted_at.isnot(None)))
    ).scalar() or 0
    # Both kinds — a thread reported as a whole counts the same as a single
    # message; the stat is "things waiting on an admin", not "reported posts".
    pending_reports_count = ((
        await db.execute(
            select(func.count()).select_from(ForumPostReportModel).where(ForumPostReportModel.resolved_at.is_(None))
        )
    ).scalar() or 0) + ((
        await db.execute(
            select(func.count()).select_from(ForumThreadReportModel).where(ForumThreadReportModel.resolved_at.is_(None))
        )
    ).scalar() or 0)
    recent_errors_count = (
        await db.execute(
            select(func.count()).select_from(ErrorLogModel)
            .where(ErrorLogModel.created_at > datetime.now(timezone.utc) - timedelta(hours=24))
        )
    ).scalar() or 0

    return {
        "users_count": users_count,
        "strategies_count": strategies_count,
        "maps_count": maps_count,
        "transactions_count": transactions_count,
        "active_subscriptions_count": active_subscriptions_count,
        "open_tickets_count": open_tickets_count,
        "pending_deleted_posts_count": pending_deleted_posts_count,
        "pending_reports_count": pending_reports_count,
        "recent_errors_count": recent_errors_count,
    }


# ─────────────────────────────────────────────
#  Maps
# ─────────────────────────────────────────────

@router.get("/admin/maps", response_model=MapsListResponse)
async def admin_list_maps(
    db: DBSession,
    admin_user: AdminUser,
    search: str | None = Query(None, description="Matches map name"),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = select(MapModel)
    count_query = select(func.count()).select_from(MapModel)

    if search:
        query = query.where(MapModel.name.ilike(f"%{search}%"))
        count_query = count_query.where(MapModel.name.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(MapModel.id).limit(limit).offset(offset))
    return MapsListResponse(total=total, maps=result.scalars().all())


@router.post("/admin/maps", response_model=MapResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_map(payload: MapCreate, db: DBSession, admin_user: AdminUser):
    existing = await db.execute(select(MapModel).where(MapModel.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A map with this name already exists")

    map_ = MapModel(**payload.model_dump())
    db.add(map_)
    await db.commit()
    await db.refresh(map_)
    return map_


@router.patch("/admin/maps/{map_id}", response_model=MapResponse)
async def admin_update_map(map_id: int, payload: MapUpdate, db: DBSession, admin_user: AdminUser):
    map_ = await db.get(MapModel, map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(map_, field, value)

    await db.commit()
    await db.refresh(map_)
    return map_


# ─────────────────────────────────────────────
#  Strategies
# ─────────────────────────────────────────────

async def _resolve_buy_tags(db, tag_ids: list[int]) -> list[BuyTagModel]:
    if not tag_ids:
        return []
    result = await db.execute(select(BuyTagModel).where(BuyTagModel.id.in_(tag_ids)))
    tags = result.scalars().all()
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more buy_tag_ids are invalid")
    return tags


def _strategy_detail_query():
    return select(StrategyModel).options(
        selectinload(StrategyModel.buy_tags),
        selectinload(StrategyModel.images),
        selectinload(StrategyModel.grenades),
        selectinload(StrategyModel.player_paths),
    )


def _hydrate_preview(strategy: StrategyModel) -> StrategyDetailResponse:
    sorted_images = sorted(strategy.images, key=lambda i: i.order)
    detail = StrategyDetailResponse.model_validate(strategy)
    detail.main_image_url = sorted_images[0].image_url if sorted_images else None
    return detail


@router.get("/admin/strategies", response_model=AdminStrategiesListResponse)
async def admin_list_strategies(
    db: DBSession,
    admin_user: AdminUser,
    map_id: int | None = Query(None),
    search: str | None = Query(None, description="Matches title or strategy ID"),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = _strategy_detail_query().order_by(StrategyModel.created_at.desc())
    count_query = select(func.count()).select_from(StrategyModel)

    if map_id is not None:
        query = query.where(StrategyModel.map_id == map_id)
        count_query = count_query.where(StrategyModel.map_id == map_id)
    if search:
        # Matching the id as text means a pasted UUID finds its strategy, and
        # so does a fragment of one — which is what you actually have to hand
        # when something references a strategy by id (a log line, a URL, a
        # bug report) and the title isn't in front of you.
        term = f"%{search.strip()}%"
        condition = or_(StrategyModel.title.ilike(term), cast(StrategyModel.id, Text).ilike(term))
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    strategies = result.scalars().unique().all()
    return AdminStrategiesListResponse(total=total, strategies=[_hydrate_preview(s) for s in strategies])


@router.post("/admin/strategies", response_model=StrategyDetailResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_strategy(payload: StrategyCreate, db: DBSession, admin_user: AdminUser):
    map_ = await db.get(MapModel, payload.map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="map_id does not exist")

    buy_tags = await _resolve_buy_tags(db, payload.buy_tag_ids)

    strategy = StrategyModel(
        map_id=payload.map_id,
        title=payload.title,
        side=payload.side,
        plant=payload.plant,
        speed=payload.speed,
        difficulty_stars=payload.difficulty_stars,
        success_rate=payload.success_rate,
        author=payload.author,
        is_free=payload.is_free,
        roles_description=payload.roles_description,
        timings_description=payload.timings_description,
        annotations=payload.annotations.model_dump(),
        buy_tags=buy_tags,
        grenades=[GrenadeModel(**g.model_dump()) for g in payload.grenades],
        images=[ImageModel(**i.model_dump()) for i in payload.images],
        player_paths=[PlayerPathModel(**p.model_dump()) for p in payload.player_paths],
    )
    db.add(strategy)
    await db.commit()

    try:
        await notify_favorited_map_users(db, map_.id, map_.name, strategy.title)
    except Exception:
        logger.exception("Failed to notify favorited-map users for strategy_id=%s", strategy.id)

    result = await db.execute(_strategy_detail_query().where(StrategyModel.id == strategy.id))
    return _hydrate_preview(result.scalar_one())


@router.patch("/admin/strategies/{strategy_id}", response_model=StrategyDetailResponse)
async def admin_update_strategy(strategy_id: uuid.UUID, payload: StrategyUpdate, db: DBSession, admin_user: AdminUser):
    result = await db.execute(_strategy_detail_query().where(StrategyModel.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    map_ = await db.get(MapModel, payload.map_id)
    if map_ is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="map_id does not exist")

    buy_tags = await _resolve_buy_tags(db, payload.buy_tag_ids)

    strategy.map_id = payload.map_id
    strategy.title = payload.title
    strategy.side = payload.side
    strategy.plant = payload.plant
    strategy.speed = payload.speed
    strategy.difficulty_stars = payload.difficulty_stars
    strategy.success_rate = payload.success_rate
    strategy.author = payload.author
    strategy.is_free = payload.is_free
    strategy.roles_description = payload.roles_description
    strategy.timings_description = payload.timings_description
    strategy.annotations = payload.annotations.model_dump()
    strategy.buy_tags = buy_tags
    # Reassigning the collections triggers delete-orphan cleanup on the rows
    # that dropped out, and inserts the new ones — a full replace per submit.
    strategy.grenades = [GrenadeModel(**g.model_dump()) for g in payload.grenades]
    strategy.images = [ImageModel(**i.model_dump()) for i in payload.images]
    strategy.player_paths = [PlayerPathModel(**p.model_dump()) for p in payload.player_paths]

    await db.commit()

    result = await db.execute(_strategy_detail_query().where(StrategyModel.id == strategy_id))
    return _hydrate_preview(result.scalar_one())


@router.delete("/admin/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_strategy(strategy_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    strategy = await db.get(StrategyModel, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    await db.delete(strategy)
    await db.commit()


@router.get("/admin/buy-tags")
async def admin_list_buy_tags(db: DBSession, admin_user: AdminUser):
    result = await db.execute(select(BuyTagModel).order_by(BuyTagModel.id))
    return [{"id": t.id, "name": t.name} for t in result.scalars().all()]


# ─────────────────────────────────────────────
#  Promo codes
# ─────────────────────────────────────────────

@router.get("/admin/promo-codes", response_model=PromoCodesListResponse)
async def admin_list_promo_codes(
    db: DBSession,
    admin_user: AdminUser,
    search: str | None = Query(None, description="Matches the promo code"),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = select(PromoCodeModel).options(selectinload(PromoCodeModel.case))
    count_query = select(func.count()).select_from(PromoCodeModel)

    if search:
        query = query.where(PromoCodeModel.code.ilike(f"%{search}%"))
        count_query = count_query.where(PromoCodeModel.code.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.order_by(PromoCodeModel.code).limit(limit).offset(offset))
    return PromoCodesListResponse(total=total, promo_codes=[_promo_out(p) for p in result.scalars().all()])


def _promo_out(promo: PromoCodeModel) -> PromoCodeOut:
    return PromoCodeOut(
        id=promo.id, code=promo.code, reward_type=promo.reward_type, coin_reward=promo.coin_reward,
        premium_days=promo.premium_days, case_id=promo.case_id, case_quantity=promo.case_quantity,
        case_name=promo.case.name if promo.case else None,
        is_active=promo.is_active, activations_limit=promo.activations_limit, used_count=promo.used_count,
    )


@router.post("/admin/promo-codes", response_model=PromoCodeOut, status_code=status.HTTP_201_CREATED)
async def admin_create_promo_code(payload: PromoCodeCreate, db: DBSession, admin_user: AdminUser):
    code = (payload.code or generate_promo_code()).strip().upper()

    existing = await db.execute(select(PromoCodeModel).where(PromoCodeModel.code == code))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This code already exists")

    case = None
    if payload.reward_type == "case":
        case = await db.get(CaseModel, payload.case_id)
        if case is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    promo = PromoCodeModel(
        code=code,
        reward_type=payload.reward_type,
        coin_reward=payload.coin_reward if payload.reward_type == "coins" else 0,
        premium_days=payload.premium_days if payload.reward_type == "premium" else None,
        case_id=payload.case_id if payload.reward_type == "case" else None,
        case_quantity=payload.case_quantity,
        activations_limit=payload.activations_limit,
        is_active=True,
        used_count=0,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    promo.case = case
    return _promo_out(promo)


@router.patch("/admin/promo-codes/{promo_id}", response_model=PromoCodeOut)
async def admin_toggle_promo_code(promo_id: uuid.UUID, payload: PromoCodeToggle, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(PromoCodeModel).options(selectinload(PromoCodeModel.case)).where(PromoCodeModel.id == promo_id)
    )
    promo = result.scalar_one_or_none()
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found")
    promo.is_active = payload.is_active
    await db.commit()
    await db.refresh(promo, attribute_names=["is_active"])
    return _promo_out(promo)


# ─────────────────────────────────────────────
#  Users
# ─────────────────────────────────────────────

@router.get("/admin/users", response_model=UsersListResponse)
async def admin_list_users(
    db: DBSession,
    admin_user: AdminUser,
    search: str | None = Query(None, description="Matches username, nickname, wallet ID, Telegram ID or user ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(UserModel).options(selectinload(UserModel.wallet)).order_by(UserModel.created_at.desc())
    count_query = select(func.count()).select_from(UserModel)

    if search:
        # Whatever identifier you happen to be holding: a @username, the
        # wallet ID from a transaction, the Telegram ID from a support
        # ticket, or the internal UUID from a log line.
        term = f"%{search.strip()}%"
        condition = or_(
            UserModel.username.ilike(term),
            UserModel.display_name.ilike(term),
            WalletModel.wallet_id.ilike(term),
            cast(UserModel.telegram_id, Text).ilike(term),
            cast(UserModel.id, Text).ilike(term),
        )
        query = query.join(UserModel.wallet).where(condition)
        count_query = count_query.join(UserModel.wallet).where(condition)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    users = result.scalars().all()

    return UsersListResponse(total=total, users=users)


@router.patch("/admin/users/{user_id}/admin", response_model=UserAdminOut)
async def admin_set_user_admin(user_id: uuid.UUID, payload: SetAdminRequest, db: DBSession, admin_user: AdminUser):
    if user_id == admin_user.id and not payload.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't remove your own admin access")

    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_admin = payload.is_admin
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/ban", response_model=UserAdminOut)
async def admin_set_user_banned(user_id: uuid.UUID, payload: SetBannedRequest, db: DBSession, admin_user: AdminUser):
    if user_id == admin_user.id and payload.is_banned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't ban your own account")

    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_banned = payload.is_banned
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/trade-ban", response_model=UserAdminOut)
async def admin_set_user_trade_banned(
    user_id: uuid.UUID, payload: SetTradeBannedRequest, db: DBSession, admin_user: AdminUser
):
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_trade_banned = payload.is_trade_banned
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/nickname", response_model=UserAdminOut)
async def admin_set_user_nickname(user_id: uuid.UUID, payload: SetNicknameRequest, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.display_name = payload.nickname
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/admin/users/{user_id}/avatar", response_model=UserAdminOut)
async def admin_clear_user_avatar(user_id: uuid.UUID, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.avatar_url = None
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/avatar", response_model=UserAdminOut)
async def admin_set_user_avatar(user_id: uuid.UUID, payload: UpdateAvatarRequest, db: DBSession, admin_user: AdminUser):
    """Lets an admin set (not just clear) any player's avatar — e.g. after
    uploading a replacement image via POST /admin/uploads."""
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.avatar_url = payload.avatar_url
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/premium", response_model=UserAdminOut)
async def admin_set_user_premium(user_id: uuid.UUID, payload: AdminSetPremiumRequest, db: DBSession, admin_user: AdminUser):
    """Sets the expiry to an ABSOLUTE now + duration, overwriting whatever
    was left — the same semantics every other grant path now uses (see
    backend/app/services/subscription.py), just at arbitrary units. E.g. a
    user with a month left gets set to exactly 1 minute if the admin picks
    unit=minute, amount=1."""
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    now = datetime.now(timezone.utc)
    wallet = user.wallet
    if payload.unit == "forever":
        wallet.is_lifetime = True
        wallet.subscription_expires_at = now + timedelta(days=365 * LIFETIME_YEARS)
        wallet.last_plan_months = None
    else:
        wallet.is_lifetime = False
        delta = {
            "month": timedelta(days=30 * payload.amount),
            "hour": timedelta(hours=payload.amount),
            "minute": timedelta(minutes=payload.amount),
        }[payload.unit]
        wallet.subscription_expires_at = now + delta
        wallet.last_plan_months = payload.amount if payload.unit == "month" else None
    wallet.reminder_sent_for_expiry = None

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/coins", response_model=UserAdminOut)
async def admin_grant_coins(user_id: uuid.UUID, payload: AdminGrantCoinsRequest, db: DBSession, admin_user: AdminUser):
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.wallet.balance_coins += payload.amount
    db.add(TransactionModel(
        sender_wallet_id=None, receiver_wallet_id=user.wallet.wallet_id,
        amount=payload.amount, transaction_type="admin_grant",
    ))

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/admin/users/{user_id}/subscription", response_model=UserAdminOut)
async def admin_grant_subscription(
    user_id: uuid.UUID, payload: AdminGrantSubscriptionRequest, db: DBSession, admin_user: AdminUser
):
    result = await db.execute(
        select(UserModel).options(selectinload(UserModel.wallet)).where(UserModel.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.months == 0:
        extend_subscription(user.wallet, "lifetime", None)
    else:
        extend_subscription(user.wallet, "premium", payload.months)

    await db.commit()
    await db.refresh(user)
    return user


# ─────────────────────────────────────────────
#  Transactions (P2P monitoring, MasterCoins stats)
# ─────────────────────────────────────────────

@router.get("/admin/transactions", response_model=TransactionsListResponse)
async def admin_list_transactions(
    db: DBSession,
    admin_user: AdminUser,
    transaction_type: str | None = Query(None, description="Filter by type, e.g. p2p_transfer"),
    wallet_id: str | None = Query(None, description="Matches either side of the transfer"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(TransactionModel).order_by(TransactionModel.created_at.desc())
    count_query = select(func.count()).select_from(TransactionModel)

    if transaction_type:
        query = query.where(TransactionModel.transaction_type == transaction_type)
        count_query = count_query.where(TransactionModel.transaction_type == transaction_type)
    if wallet_id:
        wid = wallet_id.strip().upper()
        condition = or_(TransactionModel.sender_wallet_id == wid, TransactionModel.receiver_wallet_id == wid)
        query = query.where(condition)
        count_query = count_query.where(condition)

    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.limit(limit).offset(offset))
    transactions = result.scalars().all()

    return TransactionsListResponse(total=total, transactions=transactions)


# ─────────────────────────────────────────────
#  Moderation queues — reports and support tickets
#
#  The forum itself only ever surfaces these in place: a flag on the one
#  thread you happen to be looking at, a ticket buried in a category you
#  have to go browse. That works as a detail view and not at all as a work
#  queue, which is what an admin actually needs — hence these two flat,
#  cross-forum lists.
# ─────────────────────────────────────────────

REPORT_EXCERPT_LEN = 240


@router.get("/admin/reports", response_model=AdminReportsListResponse)
async def list_all_reports(
    db: DBSession,
    admin_user: AdminUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Every unresolved report across the whole forum, post and thread
    reports interleaved by recency."""
    from backend.app.db.models import ForumCategoryModel, ForumPostReportModel, ForumThreadReportModel

    post_reports = (await db.execute(
        select(ForumPostReportModel)
        .options(
            selectinload(ForumPostReportModel.reporter),
            selectinload(ForumPostReportModel.post).selectinload(ForumPostModel.user),
            selectinload(ForumPostReportModel.post)
            .selectinload(ForumPostModel.thread)
            .selectinload(ForumThreadModel.category),
        )
        .where(ForumPostReportModel.resolved_at.is_(None))
    )).scalars().all()

    thread_reports = (await db.execute(
        select(ForumThreadReportModel)
        .options(
            selectinload(ForumThreadReportModel.reporter),
            selectinload(ForumThreadReportModel.thread).selectinload(ForumThreadModel.user),
            selectinload(ForumThreadReportModel.thread).selectinload(ForumThreadModel.category),
        )
        .where(ForumThreadReportModel.resolved_at.is_(None))
    )).scalars().all()

    def excerpt(text: str) -> str:
        return text[:REPORT_EXCERPT_LEN] + ("…" if len(text) > REPORT_EXCERPT_LEN else "")

    # Grouped by the item reported, not by report row: dismissing resolves
    # every open report on a post or thread at once, so a queue of
    # individual rows would shrink by three when an admin clicks Dismiss
    # once. Three people flagging the same message is one job.
    grouped: dict[tuple[str, uuid.UUID], AdminReportOut] = {}

    def add(key, build, reporter, reason, created_at):
        entry = grouped.get(key)
        if entry is None:
            entry = build()
            grouped[key] = entry
        entry.reports.append(ReporterOut(
            reporter_username=reporter.username, reporter_display_name=reporter.display_name,
            reason=reason, created_at=created_at,
        ))
        entry.last_reported_at = max(entry.last_reported_at, created_at)

    for r in post_reports:
        post = r.post
        # A report whose post was hard-deleted has nothing left to act on.
        if post is None or post.thread is None:
            continue
        add(
            ("post", post.id),
            lambda post=post, r=r: AdminReportOut(
                target_kind="post", target_id=post.id,
                thread_id=post.thread_id, thread_title=post.thread.title,
                category_key=post.thread.category.key,
                excerpt=excerpt(post.body),
                author_username=post.user.username, author_display_name=post.user.display_name,
                author_id=post.user_id,
                reports=[], last_reported_at=r.created_at,
            ),
            r.reporter, r.reason, r.created_at,
        )
    for r in thread_reports:
        thread = r.thread
        if thread is None:
            continue
        add(
            ("thread", thread.id),
            lambda thread=thread, r=r: AdminReportOut(
                target_kind="thread", target_id=thread.id,
                thread_id=thread.id, thread_title=thread.title,
                category_key=thread.category.key,
                excerpt=excerpt(thread.title),
                author_username=thread.user.username, author_display_name=thread.user.display_name,
                author_id=thread.user_id,
                reports=[], last_reported_at=r.created_at,
            ),
            r.reporter, r.reason, r.created_at,
        )

    rows = sorted(grouped.values(), key=lambda x: x.last_reported_at, reverse=True)
    for row in rows:
        row.reports.sort(key=lambda x: x.created_at, reverse=True)
    # Paginated in Python rather than SQL: these are two separate tables
    # that have to be merged and grouped before they can be sliced, and the
    # queue is small by nature — anything else means an admin isn't working
    # through it.
    return AdminReportsListResponse(total=len(rows), reports=rows[offset:offset + limit])


@router.get("/admin/tickets", response_model=AdminTicketsListResponse)
async def list_all_tickets(
    db: DBSession,
    admin_user: AdminUser,
    status_filter: str = Query("open", pattern="^(open|closed|all)$", alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    from backend.app.db.models import ForumCategoryModel

    query = (
        select(ForumThreadModel)
        .join(ForumCategoryModel, ForumThreadModel.category_id == ForumCategoryModel.id)
        .options(
            selectinload(ForumThreadModel.user),
            selectinload(ForumThreadModel.posts).selectinload(ForumPostModel.user),
        )
        .where(ForumCategoryModel.key == "support")
    )
    count_query = (
        select(func.count()).select_from(ForumThreadModel)
        .join(ForumCategoryModel, ForumThreadModel.category_id == ForumCategoryModel.id)
        .where(ForumCategoryModel.key == "support")
    )
    if status_filter != "all":
        is_closed = status_filter == "closed"
        query = query.where(ForumThreadModel.is_closed.is_(is_closed))
        count_query = count_query.where(ForumThreadModel.is_closed.is_(is_closed))

    total = (await db.execute(count_query)).scalar() or 0
    threads = (await db.execute(
        # Open tickets first, then oldest-touched first: the one that has
        # been waiting longest is the one to answer next.
        query.order_by(ForumThreadModel.is_closed, ForumThreadModel.updated_at).limit(limit).offset(offset)
    )).scalars().all()

    tickets = []
    for t in threads:
        posts = sorted(t.posts, key=lambda p: p.created_at)
        last = posts[-1] if posts else None
        tickets.append(AdminTicketOut(
            id=t.id, title=t.title, is_closed=t.is_closed,
            author_id=t.user_id,
            author_username=t.user.username, author_display_name=t.user.display_name,
            post_count=len(posts),
            awaiting_reply=bool(
                last and not last.user.is_admin and not last.user.is_ai_agent and not t.is_closed
            ),
            ai_handled=any(p.user.is_ai_agent for p in posts),
            created_at=t.created_at, updated_at=t.updated_at,
        ))
    return AdminTicketsListResponse(total=total, tickets=tickets)
