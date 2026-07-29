import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from backend.app.core.config import settings
from backend.app.bot.handlers import start
from backend.app.services.subscription_reminders import send_expiry_reminders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REMINDER_CHECK_INTERVAL_SECONDS = 15 * 60


async def _reminder_loop(bot: Bot):
    """Periodically checks for subscriptions expiring within 24h and
    notifies (or auto-renews) their owners. Runs for the lifetime of the bot
    process — a crash in one pass must not kill the loop."""
    while True:
        try:
            await send_expiry_reminders(bot, settings.webapp_url)
        except Exception:
            logger.exception("Subscription reminder pass failed")
        await asyncio.sleep(REMINDER_CHECK_INTERVAL_SECONDS)


async def main():
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    dp.include_router(start.router)

    reminder_task = asyncio.create_task(_reminder_loop(bot))

    logger.info("Starting StratMaster CS2 Bot...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        reminder_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())