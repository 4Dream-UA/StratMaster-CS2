import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from backend.app.core.config import settings
from backend.app.bot.handlers import start

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.include_router(start.router)

    logger.info("Starting StratMaster CS2 Bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())