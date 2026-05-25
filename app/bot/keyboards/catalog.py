from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.services.catalog import BlockDTO, LectureDTO, SectionDTO


CATALOG_SECTIONS_CALLBACK = "catalog:sections"
BUY_CALLBACK_PREFIX = "catalog:buy"


def section_callback(section_id: int) -> str:
    return f"catalog:section:{section_id}"


def block_callback(block_id: int) -> str:
    return f"catalog:block:{block_id}"


def lecture_callback(lecture_id: int) -> str:
    return f"catalog:lecture:{lecture_id}"


def buy_callback(item_type: str, item_id: int) -> str:
    return f"{BUY_CALLBACK_PREFIX}:{item_type}:{item_id}"


def miniapp_button(url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text="Открыть приложение",
        web_app=WebAppInfo(url=url),
    )


def build_sections_keyboard(
    sections: Iterable[SectionDTO],
    *,
    miniapp_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=section.title, callback_data=section_callback(section.id))]
        for section in sections
    ]
    if miniapp_url and _is_web_app_url(miniapp_url):
        rows.append([miniapp_button(miniapp_url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_section_keyboard(
    section_id: int,
    blocks: Iterable[BlockDTO],
    *,
    miniapp_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=_priced_title(block.title, block.price),
                callback_data=block_callback(block.id),
            ),
        ]
        for block in blocks
    ]
    if miniapp_url and _is_web_app_url(miniapp_url):
        rows.append([miniapp_button(miniapp_url)])
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад к разделам",
                callback_data=CATALOG_SECTIONS_CALLBACK,
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_block_keyboard(
    block: BlockDTO,
    lectures: Iterable[LectureDTO],
    *,
    miniapp_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"Купить блок за {_format_price(block.price)}",
                callback_data=buy_callback("block", block.id),
            ),
        ],
    ]
    rows.extend(
        [
            InlineKeyboardButton(
                text=_priced_title(lecture.title, lecture.price),
                callback_data=lecture_callback(lecture.id),
            ),
        ]
        for lecture in lectures
    )
    if miniapp_url and _is_web_app_url(miniapp_url):
        rows.append([miniapp_button(miniapp_url)])
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад к блокам",
                callback_data=section_callback(block.section_id),
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_lecture_keyboard(
    lecture: LectureDTO,
    *,
    miniapp_url: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"Купить лекцию за {_format_price(lecture.price)}",
                callback_data=buy_callback("lecture", lecture.id),
            ),
        ],
    ]
    if miniapp_url and _is_web_app_url(miniapp_url):
        rows.append([miniapp_button(miniapp_url)])
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад к лекциям",
                callback_data=block_callback(lecture.block_id),
            ),
        ],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _priced_title(title: str, price: Decimal) -> str:
    return f"{title} - {_format_price(price)}"


def _format_price(price: Decimal) -> str:
    normalized = price.quantize(Decimal("0.01"))
    if normalized == normalized.to_integral_value():
        return f"{normalized:.0f} ₽"
    return f"{normalized:.2f} ₽"


def _is_web_app_url(url: str) -> bool:
    return url.startswith("https://")
