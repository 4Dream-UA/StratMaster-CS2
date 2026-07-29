from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from backend.app.bot.keyboards.main import get_start_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎯 <b>Welcome to StratMaster CS2!</b>\n\n"
        "Master every map. Dominate every round.\n\n"
        "Tap the button below to open the app 👇",
        reply_markup=get_start_keyboard(),
    )