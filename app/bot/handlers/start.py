from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import build_main_menu_keyboard
from app.config.settings import get_settings
from app.db.repositories import UserRepository
from app.services.users import TelegramUserData, UserService


router = Router(name="start")


@router.message(CommandStart())
async def start_command(message: Message, session: AsyncSession) -> None:
    telegram_user = message.from_user
    if telegram_user is not None:
        service = UserService(
            repository=UserRepository(session),
            admin_telegram_ids=get_settings().admin_telegram_id_list,
        )
        await service.register_or_update_from_telegram(
            TelegramUserData(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            ),
        )

    await message.answer(
        "Здравствуйте! Это бот для доступа к лекциям и обучающим материалам по фармакологии.\n\n"
        "Выберите раздел в главном меню или откройте приложение.",
        reply_markup=build_main_menu_keyboard(),
    )
