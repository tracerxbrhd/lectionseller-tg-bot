from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.purchases import (
    PURCHASES_CONTENT_PREFIX,
    PURCHASES_LECTURE_PREFIX,
    PURCHASES_LIST_CALLBACK,
    build_purchased_lecture_keyboard,
    build_purchased_lectures_keyboard,
)
from app.bot.constants import (
    MAIN_MENU_ABOUT,
    MAIN_MENU_PURCHASES,
)
from app.bot.keyboards.main_menu import build_main_menu_keyboard
from app.common.enums import ContentType
from app.common.logging import get_logger
from app.config.settings import Settings, get_settings
from app.db.models import User
from app.db.repositories import AccessRepository, CatalogRepository, UserRepository
from app.services.content import (
    ContentAccessError,
    ContentItemDTO,
    ContentLibraryService,
    PurchasedLectureDTO,
)
from app.services.users import TelegramUserData, UserService


router = Router(name="menu")
logger = get_logger(__name__)


@router.message(F.text == MAIN_MENU_PURCHASES)
async def show_purchases(message: Message, session: AsyncSession) -> None:
    user = await _ensure_user(message, session)
    lectures = await _library_service(session).list_purchased_lectures(user.id)
    await message.answer(
        _render_purchased_lectures(lectures),
        reply_markup=(
            build_purchased_lectures_keyboard(lectures)
            if lectures
            else build_main_menu_keyboard()
        ),
    )


@router.callback_query(F.data == PURCHASES_LIST_CALLBACK)
async def show_purchases_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _ensure_user(callback, session)
    lectures = await _library_service(session).list_purchased_lectures(user.id)
    if callback.message is None:
        await callback.answer()
        return

    await callback.message.edit_text(
        _render_purchased_lectures(lectures),
        reply_markup=build_purchased_lectures_keyboard(lectures) if lectures else None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{PURCHASES_LECTURE_PREFIX}:"))
async def show_purchased_lecture(callback: CallbackQuery, session: AsyncSession) -> None:
    lecture_id = _last_int(callback.data)
    if lecture_id is None:
        await callback.answer("Лекция не найдена.", show_alert=True)
        return

    user = await _ensure_user(callback, session)
    service = _library_service(session)
    try:
        lecture = await service.get_purchased_lecture(user_id=user.id, lecture_id=lecture_id)
        content_items = await service.list_lecture_content(
            user_id=user.id,
            lecture_id=lecture_id,
        )
    except ContentAccessError:
        await callback.answer("У вас нет доступа к этой лекции.", show_alert=True)
        return

    if callback.message is None:
        await callback.answer()
        return

    await callback.message.edit_text(
        _render_purchased_lecture(lecture, content_items),
        reply_markup=build_purchased_lecture_keyboard(content_items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{PURCHASES_CONTENT_PREFIX}:"))
async def send_purchased_content(callback: CallbackQuery, session: AsyncSession) -> None:
    content_item_id = _last_int(callback.data)
    if content_item_id is None:
        await callback.answer("Материал не найден.", show_alert=True)
        return

    user = await _ensure_user(callback, session)
    try:
        content_item = await _library_service(session).get_content_item(
            user_id=user.id,
            content_item_id=content_item_id,
        )
    except ContentAccessError:
        await callback.answer("У вас нет доступа к этому материалу.", show_alert=True)
        return

    if callback.message is None:
        await callback.answer()
        return

    try:
        await _send_content_item(callback.message, content_item, get_settings())
    except ContentDeliveryError:
        logger.exception("Could not send content item %s", content_item.id)
        await callback.answer("Материал временно недоступен.", show_alert=True)
        return

    logger.info(
        "Content item %s was delivered to user %s.",
        content_item.id,
        user.id,
    )
    await callback.answer("Материал отправлен.")


def _library_service(session: AsyncSession) -> ContentLibraryService:
    return ContentLibraryService(
        access_repository=AccessRepository(session),
        catalog_repository=CatalogRepository(session),
    )


async def _ensure_user(event: Message | CallbackQuery, session: AsyncSession) -> User:
    telegram_user = event.from_user
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


def _render_purchased_lectures(lectures: list[PurchasedLectureDTO]) -> str:
    if not lectures:
        return (
            "<b>Мои покупки</b>\n\n"
            "У вас пока нет купленных лекций. Откройте каталог и выберите материал."
        )

    lines = [
        f"• {escape(lecture.title)} — {_format_date(lecture.purchased_at)}"
        for lecture in lectures
    ]
    return "<b>Мои покупки</b>\n\nВыберите лекцию:\n" + "\n".join(lines)


def _render_purchased_lecture(
    lecture: PurchasedLectureDTO,
    content_items: list[ContentItemDTO],
) -> str:
    parts = [
        f"<b>{escape(lecture.title)}</b>",
        f"Дата покупки: {_format_date(lecture.purchased_at)}",
    ]
    if lecture.short_description:
        parts.append(escape(lecture.short_description))

    if content_items:
        parts.append("Материалы доступны по кнопкам ниже.")
    else:
        parts.append("Материалы для этой лекции пока не добавлены.")

    return "\n\n".join(parts)


async def _send_content_item(
    message: Message,
    item: ContentItemDTO,
    settings: Settings,
) -> None:
    protect_content = item.protected_content_enabled
    caption = f"<b>{escape(item.title)}</b>"

    if item.type == ContentType.TEXT:
        if not item.text_content:
            raise ContentDeliveryError("Text content is empty.")
        await message.answer(
            f"{caption}\n\n{escape(item.text_content)}",
            protect_content=protect_content,
        )
        return

    source = _content_source(item, settings)
    await _send_file_content(
        message=message,
        item=item,
        source=source,
        caption=caption,
        protect_content=protect_content,
    )


async def _send_file_content(
    *,
    message: Message,
    item: ContentItemDTO,
    source: FSInputFile | str,
    caption: str,
    protect_content: bool,
) -> None:
    send_kwargs: dict[str, Any] = {
        "caption": caption,
        "protect_content": protect_content,
    }
    if item.type == ContentType.PDF:
        await message.answer_document(document=source, **send_kwargs)
        return
    if item.type == ContentType.VIDEO:
        await message.answer_video(video=source, **send_kwargs)
        return
    if item.type == ContentType.AUDIO:
        await message.answer_audio(audio=source, **send_kwargs)
        return
    if item.type == ContentType.IMAGE:
        await message.answer_photo(photo=source, **send_kwargs)
        return

    raise ContentDeliveryError(f"Unsupported content type: {item.type}")


def _content_source(item: ContentItemDTO, settings: Settings) -> FSInputFile | str:
    if item.telegram_file_id:
        return item.telegram_file_id
    if item.file_path:
        return FSInputFile(_resolve_local_content_path(item.file_path, settings.upload_dir))
    raise ContentDeliveryError("Content source is not set.")


def _resolve_local_content_path(file_path: str, upload_dir: str) -> Path:
    base_dir = Path(upload_dir).resolve()
    candidate = Path(file_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (base_dir / candidate).resolve()

    try:
        resolved.relative_to(base_dir)
    except ValueError as exc:
        raise ContentDeliveryError("Content path escapes upload directory.") from exc

    if not resolved.is_file():
        raise ContentDeliveryError("Content file does not exist.")
    return resolved


def _last_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.rsplit(":", maxsplit=1)[-1])
    except ValueError:
        return None


def _format_date(value: object) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%d.%m.%Y")
    return str(value)


class ContentDeliveryError(Exception):
    """Raised when content cannot be delivered through Telegram."""


@router.message(F.text == MAIN_MENU_ABOUT)
async def about_project(message: Message) -> None:
    await message.answer(
        "Проект предназначен для доступа к лекциям и обучающим материалам по фармакологии. "
        "Покупка, выдача материалов и поддержка будут подключаться поэтапно.",
        reply_markup=build_main_menu_keyboard(),
    )
