import random
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from backend.app.api.deps import CurrentUser, DBSession
from backend.app.core.rate_limit import rate_limit
from backend.app.db.models import CaseModel, CaseOpeningModel, TransactionModel
from backend.app.schemas.case import (
    CaseOpenResponse,
    CaseOpeningHistoryItem,
    CaseOpeningHistoryResponse,
    CaseOut,
)

router = APIRouter()


@router.get("/cases", response_model=List[CaseOut])
async def list_cases(db: DBSession):
    result = await db.execute(
        select(CaseModel).where(CaseModel.is_active == True).order_by(CaseModel.cost_coins)
    )
    return result.scalars().all()


@router.post(
    "/cases/{case_id}/open",
    response_model=CaseOpenResponse,
    dependencies=[Depends(rate_limit("case_open", max_requests=20, window_seconds=60))],
)
async def open_case(case_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    case_ = await db.get(CaseModel, case_id)
    if case_ is None or not case_.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    wallet = current_user.wallet
    if wallet.balance_coins < case_.cost_coins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough MasterCoins — need {case_.cost_coins}, have {wallet.balance_coins}",
        )

    rewards = case_.rewards
    chosen = random.choices(rewards, weights=[r["chance_percent"] for r in rewards], k=1)[0]
    reward_coins = chosen["coins"]

    wallet.balance_coins -= case_.cost_coins
    wallet.balance_coins += reward_coins

    db.add(TransactionModel(
        sender_wallet_id=wallet.wallet_id,
        receiver_wallet_id=wallet.wallet_id,
        amount=case_.cost_coins,
        transaction_type="case_open",
    ))
    db.add(TransactionModel(
        sender_wallet_id=None,
        receiver_wallet_id=wallet.wallet_id,
        amount=reward_coins,
        transaction_type="case_open",
    ))
    db.add(CaseOpeningModel(
        user_id=current_user.id,
        case_id=case_.id,
        coins_spent=case_.cost_coins,
        coins_won=reward_coins,
    ))

    await db.commit()

    return CaseOpenResponse(reward_coins=reward_coins, coins_spent=case_.cost_coins, new_balance=wallet.balance_coins)


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
