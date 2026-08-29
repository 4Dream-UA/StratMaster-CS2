import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import UserModel, WalletTradeBlockModel


async def assert_can_trade(db: AsyncSession, sender: UserModel, receiver_user_id: uuid.UUID) -> None:
    """Raises ValueError if sender can't send a P2P transfer / case gift /
    case sale offer to receiver_user_id — either the sender is globally
    trade-banned by an admin, or the receiver personally blocked them."""
    if sender.is_trade_banned:
        raise ValueError("Your account is restricted from trading with other players.")

    result = await db.execute(
        select(WalletTradeBlockModel).where(
            WalletTradeBlockModel.blocker_user_id == receiver_user_id,
            WalletTradeBlockModel.blocked_user_id == sender.id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise ValueError("This player isn't accepting trades from you.")
