from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.constants import (
    MAIN_MENU_ABOUT,
    MAIN_MENU_CATALOG,
    MAIN_MENU_PURCHASES,
    MAIN_MENU_SUPPORT,
)


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=MAIN_MENU_CATALOG),
                KeyboardButton(text=MAIN_MENU_PURCHASES),
            ],
            [
                KeyboardButton(text=MAIN_MENU_SUPPORT),
                KeyboardButton(text=MAIN_MENU_ABOUT),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )

