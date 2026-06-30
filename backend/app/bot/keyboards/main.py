from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from backend.app.core.config import settings


def get_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Open StratMaster",
                    web_app=WebAppInfo(url=settings.webapp_url),
                )
            ]
        ]
    )