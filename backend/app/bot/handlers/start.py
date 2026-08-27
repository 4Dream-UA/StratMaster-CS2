from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message

from backend.app.bot.keyboards.main import get_start_keyboard

router = Router()

# Maps a "/start <prefix>_<value>" deep-link payload to the in-app route it
# should open. Payloads are produced by the frontend's share/copy-link
# buttons (see frontend/src/config.js) — never trust the value beyond
# substituting it into a path segment.
DEEP_LINK_ROUTES = {
    "strategy": "strategy/{value}",
    "board": "shared-board/{value}",
}


@router.message(CommandStart(deep_link=True))
async def cmd_start_deep_link(message: Message, command: CommandObject):
    payload = command.args or ""
    prefix, _, value = payload.partition("_")
    route = DEEP_LINK_ROUTES.get(prefix)
    target_path = route.format(value=value) if route and value else ""

    await message.answer(
        "🎯 <b>Welcome to StratMaster CS2!</b>\n\n"
        "Tap below to open it 👇",
        reply_markup=get_start_keyboard(target_path),
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎯 <b>Welcome to StratMaster CS2!</b>\n\n"
        "Master every map. Dominate every round.\n\n"
        "Tap the button below to open the app 👇",
        reply_markup=get_start_keyboard(),
    )