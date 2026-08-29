import random
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import CaseInventoryModel, CaseModel, CaseOpeningModel, TransactionModel
from backend.app.schemas.case import (
    CaseBuyRequest,
    CaseBuyResponse,
    CaseInventoryItem,
    CaseOpenBulkRequest,
    CaseOpenBulkResponse,
    CaseOpeningHistoryItem,
    CaseOpeningHistoryResponse,
    CaseOut,
)

router = APIRouter()

VALID_OPEN_QUANTITIES = (1, 2, 5)


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be 1, 2 or 5")

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

    rewards_pool = case_.rewards
    reward_results = []
    for inv_row in owned:
        chosen = random.choices(rewards_pool, weights=[r["chance_percent"] for r in rewards_pool], k=1)[0]
        reward_coins = chosen["coins"]
        reward_results.append(reward_coins)
        db.add(CaseOpeningModel(
            user_id=current_user.id, case_id=case_.id,
            coins_spent=case_.cost_coins, coins_won=reward_coins,
        ))
        await db.delete(inv_row)

    total_won = sum(reward_results)
    wallet = current_user.wallet
    wallet.balance_coins += total_won

    db.add(TransactionModel(
        sender_wallet_id=None,
        receiver_wallet_id=wallet.wallet_id,
        amount=total_won,
        transaction_type="case_open",
    ))

    await db.commit()

    return CaseOpenBulkResponse(
        rewards=reward_results,
        total_won=total_won,
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
            created_at=o.created_at,
        )
        for o in openings
    ])
