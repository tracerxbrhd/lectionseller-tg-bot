from __future__ import annotations

import argparse
import asyncio
import contextlib
import signal

from app.common.logging import configure_logging, get_logger


logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lecture seller Telegram bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate that the bot entrypoint can be imported and started.",
    )
    return parser


async def run_bot_scaffold() -> None:
    from app.config.settings import get_settings

    settings = get_settings()
    if settings.bot_token is None:
        logger.warning("BOT_TOKEN is not set. Bot scaffold is running idle.")
    else:
        logger.info("Bot scaffold is running idle until Telegram handlers are implemented.")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError, RuntimeError):
            loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()


async def run_bot() -> None:
    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.exceptions import TelegramAPIError
    from aiogram.types import MenuButtonWebApp, WebAppInfo

    from app.bot.dispatcher import create_dispatcher
    from app.config.settings import get_settings
    from app.db.session import async_session_factory

    settings = get_settings()
    if settings.bot_token is None:
        await run_bot_scaffold()
        return

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = create_dispatcher(async_session_factory)
    if settings.effective_miniapp_url.startswith("https://"):
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Открыть приложение",
                    web_app=WebAppInfo(url=settings.effective_miniapp_url),
                ),
            )
        except TelegramAPIError:
            logger.exception("Could not set Telegram Mini App menu button.")

    logger.info("Starting Telegram bot polling.")
    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()


def main() -> None:
    configure_logging()
    args = build_parser().parse_args()

    if args.dry_run:
        logger.info("Bot scaffold dry-run completed.")
        return

    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
