import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.core.config import settings
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import (
    CaseInventoryModel,
    CaseModel,
    CaseOfferModel,
    CaseOpeningModel,
    TransactionModel,
    UserModel,
)
from backend.app.schemas.case import (
    CaseBuyRequest,
    CaseBuyResponse,
    CaseGiftRequest,
    CaseInventoryItem,
    CaseOfferOut,
    CaseOpenBulkRequest,
    CaseOpenBulkResponse,
    CaseOpeningHistoryItem,
    CaseOpeningHistoryResponse,
    CaseOut,
    CaseRewardResultOut,
    CaseSaleRequest,
)
from backend.app.services.case_economy import current_surplus, pick_reward, record_payout, record_spend, reward_value
from backend.app.services.notifications import send_telegram_message
from backend.app.services.subscription import grant_premium_days
from backend.app.services.trading import assert_can_trade
from backend.app.services.wallet import get_wallet_by_id

router = APIRouter()

VALID_OPEN_QUANTITIES = (1, 3, 5)


@router.get("/cases", response_model=List[CaseOut])
async def list_cases(db: DBSession):
    result = await db.execute(
        select(CaseModel).where(CaseModel.is_active == True).order_by(CaseModel.cost_coins)
    )
    return result.scalars().all()


@router.get("/cases/inventory", response_model=List[CaseInventoryItem])
async def list_inventory(db: DBSession, current_user: CurrentUser):
    result = await db.execute(
        select(CaseInventoryModel.case_id, func.count().label("count"))
        .where(CaseInventoryModel.user_id == current_user.id)
        .group_by(CaseInventoryModel.case_id)
    )
    rows = result.all()
    if not rows:
        return []

    cases_result = await db.execute(select(CaseModel).where(CaseModel.id.in_([r.case_id for r in rows])))
    cases_by_id = {c.id: c for c in cases_result.scalars().all()}

    return [
        CaseInventoryItem(case_id=r.case_id, case_name=cases_by_id[r.case_id].name, count=r.count)
        for r in rows if r.case_id in cases_by_id
    ]


@router.post(
    "/cases/{case_id}/buy",
    response_model=CaseBuyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("case_buy", max_requests=20, window_seconds=60))],
)
async def buy_case(case_id: uuid.UUID, payload: CaseBuyRequest, db: DBSession, current_user: CurrentUser):
    case_ = await db.get(CaseModel, case_id)
    if case_ is None or not case_.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    total_cost = case_.cost_coins * payload.quantity
    wallet = current_user.wallet
    if wallet.balance_coins < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough MasterCoins — need {total_cost}, have {wallet.balance_coins}",
        )

    wallet.balance_coins -= total_cost
    for _ in range(payload.quantity):
        db.add(CaseInventoryModel(user_id=current_user.id, case_id=case_.id))

    await record_spend(db, total_cost)

    db.add(TransactionModel(
        sender_wallet_id=wallet.wallet_id,
        receiver_wallet_id=wallet.wallet_id,
        amount=total_cost,
        transaction_type="case_open",
    ))

    await db.commit()

    return CaseBuyResponse(case_id=case_.id, quantity=payload.quantity, new_balance=wallet.balance_coins)


@router.post(
    "/cases/inventory/open",
    response_model=CaseOpenBulkResponse,
    dependencies=[Depends(rate_limit("case_open", max_requests=20, window_seconds=60))],
)
async def open_inventory_cases(payload: CaseOpenBulkRequest, db: DBSession, current_user: CurrentUser):
    if payload.quantity not in VALID_OPEN_QUANTITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be 1, 3 or 5")

    case_ = await db.get(CaseModel, payload.case_id)
    if case_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    # Locks the rows for the duration of this transaction — without it, two
    # concurrent x5 opens on a 5-case inventory could both "succeed" against
    # the same unlocked rows before either commits.
    result = await db.execute(
        select(CaseInventoryModel)
        .where(CaseInventoryModel.user_id == current_user.id, CaseInventoryModel.case_id == case_.id)
        .order_by(CaseInventoryModel.acquired_at)
        .limit(payload.quantity)
        .with_for_update()
    )
    owned = result.scalars().all()
    if len(owned) < payload.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You only own {len(owned)} of this case — buy more before opening {payload.quantity}",
        )

    wallet = current_user.wallet
    surplus, total_spent_coins = await current_surplus(db)
    reward_results: list[CaseRewardResultOut] = []
    total_coins_won = 0
    total_value_paid = 0
    new_expiry = None

    for inv_row in owned:
        chosen = pick_reward(case_.rewards, case_.cost_coins, surplus, total_spent_coins)
        value = reward_value(chosen)
        surplus += value  # each pick in this batch sees the running total the previous picks left behind
        total_value_paid += value

        if "premium_days" in chosen:
            days = chosen["premium_days"]
            if days > 0:
                new_expiry = grant_premium_days(wallet, days)
            db.add(CaseOpeningModel(
                user_id=current_user.id, case_id=case_.id,
                coins_spent=case_.cost_coins, coins_won=0, premium_days_won=days,
            ))
            reward_results.append(CaseRewardResultOut(coins=0, premium_days=days))
        else:
            coins = chosen["coins"]
            total_coins_won += coins
            db.add(CaseOpeningModel(
                user_id=current_user.id, case_id=case_.id,
                coins_spent=case_.cost_coins, coins_won=coins, premium_days_won=None,
            ))
            reward_results.append(CaseRewardResultOut(coins=coins, premium_days=None))
        await db.delete(inv_row)

    wallet.balance_coins += total_coins_won
    await record_payout(db, total_value_paid)

    # Logged even when a premium-days tier paid no coins at all (amount=0)
    # — the same audit-trail gap that silently broke the admin "Case Gifts"
    # filter earlier applies here just as easily otherwise.
    db.add(TransactionModel(
        sender_wallet_id=None,
        receiver_wallet_id=wallet.wallet_id,
        amount=total_coins_won,
        transaction_type="case_open",
    ))

    await db.commit()

    return CaseOpenBulkResponse(
        rewards=reward_results,
        total_won=total_coins_won,
        premium_expires_at=new_expiry,
        total_spent=case_.cost_coins * payload.quantity,
        new_balance=wallet.balance_coins,
    )


@router.get("/cases/openings/history", response_model=CaseOpeningHistoryResponse)
async def case_opening_history(db: DBSession, current_user: CurrentUser):
    result = await db.execute(
        select(CaseOpeningModel)
        .where(CaseOpeningModel.user_id == current_user.id)
        .order_by(CaseOpeningModel.created_at.desc())
        .limit(10)
    )
    openings = result.scalars().all()

    case_ids = {o.case_id for o in openings}
    cases_result = await db.execute(select(CaseModel).where(CaseModel.id.in_(case_ids)))
    names_by_id = {c.id: c.name for c in cases_result.scalars().all()}

    return CaseOpeningHistoryResponse(openings=[
        CaseOpeningHistoryItem(
            id=o.id,
            case_id=o.case_id,
            case_name=names_by_id.get(o.case_id, "Unknown case"),
            coins_spent=o.coins_spent,
            coins_won=o.coins_won,
            premium_days_won=o.premium_days_won,
            created_at=o.created_at,
        )
        for o in openings
    ])


# ─────────────────────────────────────────────
#  P2P case gifting + sales — an "offer" escrows the sender's cases the
#  moment it's created; they only land in the receiver's inventory once
#  the receiver explicitly accepts (declining/cancelling returns them).
# ─────────────────────────────────────────────

def _offer_link() -> str | None:
    if not settings.webapp_url:
        return None
    return f"{settings.webapp_url.rstrip('/')}/user?tab=cases&sub=offers"


async def _escrow_cases(db, user_id: uuid.UUID, case_id: uuid.UUID, quantity: int) -> None:
    result = await db.execute(
        select(CaseInventoryModel)
        .where(CaseInventoryModel.user_id == user_id, CaseInventoryModel.case_id == case_id)
        .order_by(CaseInventoryModel.acquired_at)
        .limit(quantity)
        .with_for_update()
    )
    owned = result.scalars().all()
    if len(owned) < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You only own {len(owned)} of this case",
        )
    for row in owned:
        await db.delete(row)


async def _create_offer(db, sender, receiver_wallet_id: str, case_id: uuid.UUID, quantity: int, price_coins: int, offer_type: str) -> CaseOfferModel:
    case_ = await db.get(CaseModel, case_id)
    if case_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    receiver_wallet = await get_wallet_by_id(db, receiver_wallet_id)
    if receiver_wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No wallet found with this ID")
    if receiver_wallet.user_id == sender.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You can't send an offer to yourself")

    try:
        await assert_can_trade(db, sender, receiver_wallet.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    await _escrow_cases(db, sender.id, case_.id, quantity)

    offer = CaseOfferModel(
        sender_user_id=sender.id, receiver_user_id=receiver_wallet.user_id, case_id=case_.id,
        quantity=quantity, price_coins=price_coins, offer_type=offer_type, status="pending",
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)

    receiver_user = await db.get(UserModel, receiver_wallet.user_id)
    verb = "gifted you" if offer_type == "gift" else f"wants to sell you for {price_coins} MC"
    sender_name = f"@{sender.username}" if sender.username else "A player"
    text = f"🎁 {sender_name} {verb} {quantity}× {case_.name} — open the app to accept or decline."
    await send_telegram_message(receiver_user.telegram_id, text, web_app_url=_offer_link())

    return offer


async def _get_offer_or_404(db, offer_id: uuid.UUID) -> CaseOfferModel:
    result = await db.execute(
        select(CaseOfferModel)
        .options(
            selectinload(CaseOfferModel.case),
            selectinload(CaseOfferModel.sender).selectinload(UserModel.wallet),
            selectinload(CaseOfferModel.receiver).selectinload(UserModel.wallet),
        )
        .where(CaseOfferModel.id == offer_id)
    )
    offer = result.scalar_one_or_none()
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    return offer


def _offer_out(o: CaseOfferModel) -> CaseOfferOut:
    return CaseOfferOut(
        id=o.id,
        sender_wallet_id=o.sender.wallet.wallet_id, sender_username=o.sender.username,
        receiver_wallet_id=o.receiver.wallet.wallet_id, receiver_username=o.receiver.username,
        case_id=o.case_id, case_name=o.case.name,
        quantity=o.quantity, price_coins=o.price_coins, offer_type=o.offer_type,
        status=o.status, created_at=o.created_at,
    )


@router.post(
    "/cases/gift", response_model=CaseOfferOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("case_offer", max_requests=15, window_seconds=60))],
)
async def gift_case(payload: CaseGiftRequest, db: DBSession, current_user: CurrentUser):
    offer = await _create_offer(db, current_user, payload.receiver_wallet_id, payload.case_id, payload.quantity, 0, "gift")
    return await _get_offer_or_404_out(db, offer.id)


@router.post(
    "/cases/sell", response_model=CaseOfferOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("case_offer", max_requests=15, window_seconds=60))],
)
async def sell_case(payload: CaseSaleRequest, db: DBSession, current_user: CurrentUser):
    offer = await _create_offer(
        db, current_user, payload.receiver_wallet_id, payload.case_id, payload.quantity, payload.price_coins, "sale",
    )
    return await _get_offer_or_404_out(db, offer.id)


async def _get_offer_or_404_out(db, offer_id: uuid.UUID) -> CaseOfferOut:
    return _offer_out(await _get_offer_or_404(db, offer_id))


@router.get("/cases/offers", response_model=List[CaseOfferOut])
async def list_offers(db: DBSession, current_user: CurrentUser, direction: str = "incoming"):
    if direction not in ("incoming", "outgoing"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="direction must be 'incoming' or 'outgoing'")

    column = CaseOfferModel.receiver_user_id if direction == "incoming" else CaseOfferModel.sender_user_id
    result = await db.execute(
        select(CaseOfferModel)
        .options(
            selectinload(CaseOfferModel.case),
            selectinload(CaseOfferModel.sender).selectinload(UserModel.wallet),
            selectinload(CaseOfferModel.receiver).selectinload(UserModel.wallet),
        )
        .where(column == current_user.id, CaseOfferModel.status == "pending")
        .order_by(CaseOfferModel.created_at.desc())
    )
    return [_offer_out(o) for o in result.scalars().all()]


@router.post("/cases/offers/{offer_id}/accept", response_model=CaseOfferOut)
async def accept_offer(offer_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    offer = await _get_offer_or_404(db, offer_id)
    if offer.receiver_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This isn't your offer to accept")
    if offer.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This offer is no longer pending")

    if offer.offer_type == "sale":
        receiver_wallet = current_user.wallet
        if receiver_wallet.balance_coins < offer.price_coins:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough MasterCoins — need {offer.price_coins}, have {receiver_wallet.balance_coins}",
            )
        sender_wallet = offer.sender.wallet
        receiver_wallet.balance_coins -= offer.price_coins
        sender_wallet.balance_coins += offer.price_coins
        db.add(TransactionModel(
            sender_wallet_id=receiver_wallet.wallet_id, receiver_wallet_id=sender_wallet.wallet_id,
            amount=offer.price_coins, transaction_type="case_sale",
        ))
    else:
        # No coins change hands for a gift, but still logged (amount=0) so
        # it shows up in the admin transaction audit trail.
        db.add(TransactionModel(
            sender_wallet_id=offer.sender.wallet.wallet_id, receiver_wallet_id=current_user.wallet.wallet_id,
            amount=0, transaction_type="case_gift",
        ))

    for _ in range(offer.quantity):
        db.add(CaseInventoryModel(user_id=current_user.id, case_id=offer.case_id))

    offer.status = "accepted"
    offer.resolved_at = datetime.now(timezone.utc)
    await db.commit()

    verb = "accepted your gift" if offer.offer_type == "gift" else "bought"
    receiver_name = f"@{current_user.username}" if current_user.username else "The recipient"
    await send_telegram_message(
        offer.sender.telegram_id,
        f"✅ {receiver_name} {verb} {offer.quantity}× {offer.case.name}.",
        web_app_url=_offer_link(),
    )

    return await _get_offer_or_404_out(db, offer.id)


async def _return_escrow(db, offer: CaseOfferModel) -> None:
    for _ in range(offer.quantity):
        db.add(CaseInventoryModel(user_id=offer.sender_user_id, case_id=offer.case_id))


@router.post("/cases/offers/{offer_id}/decline", response_model=CaseOfferOut)
async def decline_offer(offer_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    offer = await _get_offer_or_404(db, offer_id)
    if offer.receiver_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This isn't your offer to decline")
    if offer.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This offer is no longer pending")

    await _return_escrow(db, offer)
    offer.status = "declined"
    offer.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return await _get_offer_or_404_out(db, offer.id)


@router.post("/cases/offers/{offer_id}/cancel", response_model=CaseOfferOut)
async def cancel_offer(offer_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    offer = await _get_offer_or_404(db, offer_id)
    if offer.sender_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This isn't your offer to cancel")
    if offer.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This offer is no longer pending")

    await _return_escrow(db, offer)
    offer.status = "cancelled"
    offer.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return await _get_offer_or_404_out(db, offer.id)
