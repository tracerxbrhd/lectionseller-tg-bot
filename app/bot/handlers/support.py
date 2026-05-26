from __future__ import annotations

from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.constants import MAIN_MENU_SUPPORT, SUPPORT_CANCEL
from app.bot.keyboards.main_menu import build_main_menu_keyboard
from app.bot.keyboards.support import build_support_cancel_keyboard
from app.bot.states import SupportRequestStates
from app.common.logging import get_logger
from app.config.settings import get_settings
from app.db.models import User
from app.db.repositories import SupportRepository, UserRepository
from app.services.support import SupportRequestDTO, SupportRequestError, SupportService
from app.services.users import TelegramUserData, UserService


router = Router(name="support")
logger = get_logger(__name__)


@router.message(F.text == MAIN_MENU_SUPPORT)
async def start_support_request(message: Message, state: FSMContext) -> None:
    await state.set_state(SupportRequestStates.waiting_for_message)
    await message.answer(
        "<b>Поддержка</b>\n\n"
        "Напишите вопрос одним сообщением. Лучше сразу укажите, что произошло: "
        "оплата, доступ к материалам, ошибка загрузки или другой вопрос.\n\n"
        "<b>Статус:</b> обращение будет сохранено и передано администратору.",
        reply_markup=build_support_cancel_keyboard(),
    )


@router.message(SupportRequestStates.waiting_for_message, F.text == SUPPORT_CANCEL)
@router.message(SupportRequestStates.waiting_for_message, F.text == "/cancel")
async def cancel_support_request(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Обращение отменено.</b>\n\n"
        "Вы можете вернуться в поддержку в любой момент.",
        reply_markup=build_main_menu_keyboard(),
    )


@router.message(SupportRequestStates.waiting_for_message)
async def submit_support_request(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    if not message.text:
        await message.answer(
            "<b>Нужен текстовый вопрос.</b>\n\n"
            "Пожалуйста, отправьте обращение одним текстовым сообщением."
        )
        return

    user = await _ensure_user(message, session)
    service = SupportService(SupportRepository(session))
    try:
        support_request = await service.create_request(
            user_id=user.id,
            message=message.text,
        )
    except SupportRequestError:
        await message.answer(
            "<b>Сообщение не подходит по длине.</b>\n\n"
            "Напишите от 5 до 4000 символов и отправьте вопрос еще раз.",
            reply_markup=build_support_cancel_keyboard(),
        )
        return

    await state.clear()
    await _notify_admins(bot, support_request, user)
    await message.answer(
        f"<b>Обращение #{support_request.id} принято</b>\n\n"
        "<b>Статус:</b> <code>ОТКРЫТО</code>\n\n"
        "Администратор увидит ваш вопрос и ответит позже.",
        reply_markup=build_main_menu_keyboard(),
    )


async def _ensure_user(message: Message, session: AsyncSession) -> User:
    telegram_user = message.from_user
    if telegram_user is None:
        raise RuntimeError("Telegram user is missing in support message.")

    service = UserService(
        repository=UserRepository(session),
        admin_telegram_ids=get_settings().admin_telegram_id_list,
    )
    return await service.register_or_update_from_telegram(
        TelegramUserData(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
        ),
    )


async def _notify_admins(
    bot: Bot,
    support_request: SupportRequestDTO,
    user: User,
) -> None:
    admin_ids = get_settings().admin_telegram_id_list
    if not admin_ids:
        logger.warning(
            "Support request %s created, but no admin IDs configured.",
            support_request.id,
        )
        return

    text = _render_admin_notification(support_request, user)
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except TelegramAPIError:
            logger.exception(
                "Could not notify admin %s about support request %s.",
                admin_id,
                support_request.id,
            )


def _render_admin_notification(support_request: SupportRequestDTO, user: User) -> str:
    username = f"@{user.username}" if user.username else "без username"
    full_name = " ".join(
        part for part in [user.first_name, user.last_name] if part
    ) or "имя не указано"
    return (
        f"<b>Новое обращение #{support_request.id}</b>\n\n"
        f"Пользователь: {escape(full_name)} ({escape(username)})\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n\n"
        f"{escape(support_request.message)}"
    )
