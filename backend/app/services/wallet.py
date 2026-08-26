from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import WalletModel


async def get_wallet_by_id(db: AsyncSession, wallet_id: str) -> WalletModel | None:
    result = await db.execute(
        select(WalletModel).where(WalletModel.wallet_id == wallet_id.strip().upper())
    )
    return result.scalar_one_or_none()


def assert_transferable(sender: WalletModel, receiver: WalletModel | None, amount: int) -> None:
    """Validates a P2P coin transfer before any balance is touched.

    Raises LookupError if the receiver wallet doesn't exist, ValueError for
    any other rule violation — the router maps these to 404 / 400. Because
    this runs entirely before the caller mutates any balance, a rejected
    transfer never partially applies: the sender's coins never leave their
    wallet unless every check here passes.
    """
    if receiver is None:
        raise LookupError("No wallet found with this ID")
    if receiver.id == sender.id:
        raise ValueError("You can't send coins to your own wallet")
    if sender.balance_coins < amount:
        raise ValueError(f"Not enough MasterCoins — need {amount}, have {sender.balance_coins}")
