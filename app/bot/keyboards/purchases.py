from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_purchased_lecture_keyboard(
    content_items: Iterable[ContentItemDTO],
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
