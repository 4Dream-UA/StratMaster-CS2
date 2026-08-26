import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.models import FavoriteMapModel, UserModel

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


async def send_telegram_message(telegram_id: int, text: str, web_app_url: str | None = None) -> None:
    """Sends a plain Telegram message via the Bot API's raw HTTP endpoint.

    The FastAPI process doesn't run its own aiogram Dispatcher (that's
    main_bot.py's job) — this is a lightweight direct call instead of
    standing up a second bot instance just to send one message. Failures
    are logged and swallowed: a notification is best-effort and must never
    fail the request that triggered it (e.g. an admin creating a strategy).
    """
    if not settings.bot_token:
        return

    payload = {"chat_id": telegram_id, "text": text, "parse_mode": "HTML"}
    if web_app_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": "Open StratMaster", "web_app": {"url": web_app_url}}]]
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{TELEGRAM_API_BASE}/bot{settings.bot_token}/sendMessage", json=payload)
    except Exception:
        logger.exception("Failed to send Telegram notification to telegram_id=%s", telegram_id)


async def notify_favorited_map_users(
    db: AsyncSession, map_id: int, map_name: str, strategy_title: str
) -> None:
    """Notifies every user who favorited `map_id` that a new strategy was
    added to it — the payoff for favoriting a map in the first place."""
    result = await db.execute(
        select(UserModel)
        .join(FavoriteMapModel, FavoriteMapModel.user_id == UserModel.id)
        .where(FavoriteMapModel.map_id == map_id)
    )
    users = result.scalars().all()
    if not users:
        return

    text = f"🔥 New strategy on <b>{map_name}</b>: {strategy_title}"
    web_app_url = f"{settings.webapp_url.rstrip('/')}/map/{map_id}" if settings.webapp_url else None

    for user in users:
        await send_telegram_message(user.telegram_id, text, web_app_url=web_app_url)
