from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.services.content import ContentItemDTO, PurchasedLectureDTO


PURCHASES_LIST_CALLBACK = "purchases:list"
PURCHASES_LECTURE_PREFIX = "purchases:lecture"
PURCHASES_CONTENT_PREFIX = "purchases:content"


def purchased_lecture_callback(lecture_id: int) -> str:
    return f"{PURCHASES_LECTURE_PREFIX}:{lecture_id}"


def purchased_content_callback(content_item_id: int) -> str:
    return f"{PURCHASES_CONTENT_PREFIX}:{content_item_id}"


def build_purchased_lectures_keyboard(
    lectures: Iterable[PurchasedLectureDTO],
    *,
    miniapp_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=lecture.title,
                callback_data=purchased_lecture_callback(lecture.id),
            ),
        ]
        for lecture in lectures
    ]
    if miniapp_url and _is_web_app_url(miniapp_url):
        rows.append([_miniapp_button(miniapp_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_purchased_lecture_keyboard(
    content_items: Iterable[ContentItemDTO],
    *,
    miniapp_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{_content_type_title(item)} {item.title}",
                callback_data=purchased_content_callback(item.id),
            ),
        ]
        for item in content_items
    ]
    if miniapp_url and _is_web_app_url(miniapp_url):
        rows.append([_miniapp_button(miniapp_url)])
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад к покупкам",
                callback_data=PURCHASES_LIST_CALLBACK,
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _content_type_title(item: ContentItemDTO) -> str:
    return {
        "pdf": "PDF:",
        "video": "Видео:",
        "audio": "Аудио:",
        "image": "Изображение:",
        "text": "Текст:",
    }.get(item.type.value, "Материал:")


def _is_web_app_url(url: str) -> bool:
    return url.startswith("https://")


def _miniapp_button(url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="Открыть приложение",
        web_app=WebAppInfo(url=url),
    )
