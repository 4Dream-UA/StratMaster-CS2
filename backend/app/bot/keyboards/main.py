from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from backend.app.core.config import settings


def get_start_keyboard(target_path: str = "") -> InlineKeyboardMarkup:
    """target_path (e.g. "strategy/<id>") opens the Mini App directly on
    that page — used for deep links shared outside the bot chat, since
    Telegram only lets a web_app button's URL be set when the bot sends
    the message, never from a bare link someone pastes elsewhere."""
    url = f"{settings.webapp_url.rstrip('/')}/{target_path}" if target_path else settings.webapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Open StratMaster",
                    web_app=WebAppInfo(url=url),
                )
            ]
        ]
    )