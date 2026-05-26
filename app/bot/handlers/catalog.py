from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.constants import MAIN_MENU_CATALOG
from app.bot.keyboards.catalog import (
    BUY_CALLBACK_PREFIX,
    CATALOG_SECTIONS_CALLBACK,
    block_callback,
    build_block_keyboard,
    build_lecture_keyboard,
    build_section_keyboard,
    build_sections_keyboard,
    lecture_callback,
    section_callback,
)
from app.bot.keyboards.main_menu import build_main_menu_keyboard
from app.bot.keyboards.payments import build_payment_keyboard
from app.common.enums import PurchaseType
from app.common.logging import get_logger
from app.config.settings import get_settings
from app.db.models import User
from app.db.repositories import (
    CatalogRepository,
    PaymentRepository,
    PurchaseRepository,
    UserRepository,
)
from app.services.catalog import BlockDTO, CatalogService, LectureDTO, SectionDTO
from app.services.payments import (
    CheckoutService,
    PaymentConfigurationError,
    PaymentProviderError,
    YooKassaPaymentService,
)
from app.services.purchases import PurchaseError, PurchaseService
from app.services.users import TelegramUserData, UserService


router = Router(name="catalog")
logger = get_logger(__name__)


@router.message(F.text == MAIN_MENU_CATALOG)
async def catalog_menu(message: Message, session: AsyncSession) -> None:
    service = _catalog_service(session)
    sections = await service.list_sections()
    await message.answer(
        _render_sections(sections),
        reply_markup=build_sections_keyboard(
            sections,
            miniapp_url=get_settings().effective_miniapp_url,
        ),
    )


@router.callback_query(F.data == CATALOG_SECTIONS_CALLBACK)
async def show_sections(callback: CallbackQuery, session: AsyncSession) -> None:
    service = _catalog_service(session)
    sections = await service.list_sections()
    await _edit_catalog_message(
        callback,
        _render_sections(sections),
        build_sections_keyboard(
            sections,
            miniapp_url=get_settings().effective_miniapp_url,
        ),
    )


@router.callback_query(F.data.startswith("catalog:section:"))
async def show_section(callback: CallbackQuery, session: AsyncSession) -> None:
    section_id = _last_int(callback.data)
    if section_id is None:
        await callback.answer("Раздел не найден.", show_alert=True)
        return

    service = _catalog_service(session)
    section = await service.get_section(section_id)
    if section is None:
        await callback.answer("Раздел недоступен.", show_alert=True)
        return

    blocks = await service.list_blocks(section.id)
    await _edit_catalog_message(
        callback,
        _render_section(section, blocks),
        build_section_keyboard(
            section.id,
            blocks,
            miniapp_url=get_settings().effective_miniapp_url,
        ),
    )


@router.callback_query(F.data.startswith("catalog:block:"))
async def show_block(callback: CallbackQuery, session: AsyncSession) -> None:
    block_id = _last_int(callback.data)
    if block_id is None:
        await callback.answer("Блок не найден.", show_alert=True)
        return

    service = _catalog_service(session)
    block = await service.get_block(block_id)
    if block is None:
        await callback.answer("Блок недоступен.", show_alert=True)
        return

    lectures = await service.list_lectures(block.id)
    await _edit_catalog_message(
        callback,
        _render_block(block, lectures),
        build_block_keyboard(
            block,
            lectures,
            miniapp_url=get_settings().effective_miniapp_url,
        ),
    )


@router.callback_query(F.data.startswith("catalog:lecture:"))
async def show_lecture(callback: CallbackQuery, session: AsyncSession) -> None:
    lecture_id = _last_int(callback.data)
    if lecture_id is None:
        await callback.answer("Лекция не найдена.", show_alert=True)
        return

    service = _catalog_service(session)
    lecture = await service.get_lecture(lecture_id)
    if lecture is None:
        await callback.answer("Лекция недоступна.", show_alert=True)
        return

    await _edit_catalog_message(
        callback,
        _render_lecture(lecture),
        build_lecture_keyboard(
            lecture,
            miniapp_url=get_settings().effective_miniapp_url,
        ),
    )


@router.callback_query(F.data.startswith(f"{BUY_CALLBACK_PREFIX}:"))
async def create_pending_purchase(callback: CallbackQuery, session: AsyncSession) -> None:
    purchase_type, object_id = _parse_buy_callback(callback.data)
    if purchase_type is None or object_id is None:
        await callback.answer("Не удалось определить товар.", show_alert=True)
        return

    user = await _ensure_user(callback, session)
    if user is None:
        await callback.answer("Не удалось определить пользователя.", show_alert=True)
        return

    purchase_repository = PurchaseRepository(session)
    service = PurchaseService(
        purchase_repository=purchase_repository,
        catalog_repository=CatalogRepository(session),
    )
    try:
        purchase = await service.create_pending_purchase(
            user_id=user.id,
            purchase_type=purchase_type,
            object_id=object_id,
        )
    except PurchaseError:
        await callback.answer("Этот товар сейчас недоступен для покупки.", show_alert=True)
        return

    payment_url: str | None = None
    payment_error = False
    settings = get_settings()
    purchase_model = await purchase_repository.get(purchase.id)
    if settings.yookassa_enabled and purchase_model is not None:
        checkout_service = CheckoutService(
            payment_repository=PaymentRepository(session),
            payment_service=YooKassaPaymentService(settings),
        )
        try:
            payment = await checkout_service.get_or_create_payment(purchase_model)
        except PaymentConfigurationError:
            logger.exception("YooKassa is enabled but configuration is invalid.")
            payment_error = True
        except PaymentProviderError:
            payment_error = True
        else:
            payment_url = payment.confirmation_url

    text = (
        f"<b>Покупка #{purchase.id} создана</b>\n\n"
        f"Сумма к оплате: <b>{_format_price(purchase.price)}</b>\n"
        "<b>Статус:</b> <code>ОЖИДАЕТ ОПЛАТЫ</code>\n\n"
        f"{_payment_instruction(payment_url=payment_url, payment_error=payment_error)}"
    )
    reply_markup = (
        build_payment_keyboard(payment_url, purchase.id)
        if payment_url
        else build_main_menu_keyboard()
    )

    if callback.message is not None:
        await callback.message.answer(text, reply_markup=reply_markup)
        await callback.answer()
    else:
        await callback.answer(f"Заявка #{purchase.id} создана.", show_alert=True)


def _catalog_service(session: AsyncSession) -> CatalogService:
    return CatalogService(CatalogRepository(session))


async def _ensure_user(callback: CallbackQuery, session: AsyncSession) -> User | None:
    telegram_user = callback.from_user
    if telegram_user is None:
        return None

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


def _render_sections(sections: list[SectionDTO]) -> str:
    if not sections:
        return (
            "<b>Каталог пока пуст</b>\n\n"
            "Разделы появятся здесь после добавления в админ-панели."
        )
    return (
        "<b>Каталог лекций</b>\n\n"
        "Выберите раздел, затем блок и конкретную лекцию. "
        "Если удобнее работать в отдельном интерфейсе, откройте Mini App."
    )


def _render_section(section: SectionDTO, blocks: list[BlockDTO]) -> str:
    description = f"\n\n{escape(section.description)}" if section.description else ""
    if not blocks:
        return (
            f"<b>{escape(section.title)}</b>{description}\n\n"
            "В этом разделе пока нет активных блоков."
        )

    block_lines = "\n".join(
        f"• {escape(block.title)} - {_format_price(block.price)}" for block in blocks
    )
    return (
        f"<b>Раздел: {escape(section.title)}</b>{description}\n\n"
        "<b>Доступные блоки:</b>\n"
        f"{block_lines}"
    )


def _render_block(block: BlockDTO, lectures: list[LectureDTO]) -> str:
    description = f"\n\n{escape(block.description)}" if block.description else ""
    if not lectures:
        return (
            f"<b>Блок: {escape(block.title)}</b>{description}\n\n"
            f"Цена блока: <b>{_format_price(block.price)}</b>\n\n"
            "В этом блоке пока нет активных лекций."
        )

    lecture_lines = "\n".join(
        f"• {escape(lecture.title)} - {_format_price(lecture.price)}" for lecture in lectures
    )
    return (
        f"<b>Блок: {escape(block.title)}</b>{description}\n\n"
        f"Цена блока: <b>{_format_price(block.price)}</b>\n\n"
        f"<b>Лекции в блоке:</b>\n{lecture_lines}"
    )


def _render_lecture(lecture: LectureDTO) -> str:
    parts = [
        f"<b>Лекция: {escape(lecture.title)}</b>",
        f"Цена: <b>{_format_price(lecture.price)}</b>",
        "<b>Статус:</b> доступ откроется после оплаты.",
    ]

    if lecture.short_description:
        parts.append(escape(lecture.short_description))
    if lecture.full_description:
        parts.append(escape(lecture.full_description))

    return "\n\n".join(parts)


async def _edit_catalog_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: object,
) -> None:
    if callback.message is None:
        await callback.answer()
        return

    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer()


def _last_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.rsplit(":", maxsplit=1)[-1])
    except ValueError:
        return None


def _parse_buy_callback(value: str | None) -> tuple[PurchaseType | None, int | None]:
    if value is None:
        return None, None
    parts = value.split(":")
    if len(parts) != 4:
        return None, None

    _, _, raw_type, raw_id = parts
    try:
        return PurchaseType(raw_type), int(raw_id)
    except ValueError:
        return None, None


def _format_price(price: object) -> str:
    return f"{price:,.2f} ₽".replace(",", " ").replace(".00", "")


def _payment_instruction(*, payment_url: str | None, payment_error: bool) -> str:
    if payment_url is not None:
        return (
            "<b>Что сделать дальше:</b>\n"
            "1. Нажмите «Перейти к оплате».\n"
            "2. Завершите платеж в YooKassa.\n"
            "3. Вернитесь в бот и нажмите «Проверить статус оплаты».\n\n"
            "<b>Важно:</b> доступ появится только после подтверждения оплаты."
        )

    if payment_error:
        return (
            "<b>Статус:</b> <code>ССЫЛКА НЕ СОЗДАНА</code>\n"
            "Платежный провайдер временно не вернул ссылку. "
            "Попробуйте позже или напишите в поддержку."
        )

    return (
        "<b>Статус:</b> <code>ОПЛАТА ВРЕМЕННО НЕДОСТУПНА</code>\n"
        "Заявка сохранена. Платежная ссылка появится после настройки YooKassa."
    )
