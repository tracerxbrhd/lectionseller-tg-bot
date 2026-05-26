from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from app.bot.constants import (
    MAIN_MENU_ABOUT,
    MAIN_MENU_CATALOG,
    MAIN_MENU_MINIAPP,
    MAIN_MENU_PURCHASES,
    MAIN_MENU_SUPPORT,
)
from app.config.settings import get_settings


def build_main_menu_keyboard() -> ReplyKeyboardMarkup:
    miniapp_url = get_settings().effective_miniapp_url
    miniapp_button = KeyboardButton(text=MAIN_MENU_MINIAPP)
    if _is_web_app_url(miniapp_url):
        miniapp_button = KeyboardButton(
            text=MAIN_MENU_MINIAPP,
            web_app=WebAppInfo(url=miniapp_url),
        )

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                miniapp_button,
            ],
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
        input_field_placeholder="Выберите действие",
    )


def _is_web_app_url(url: str) -> bool:
    return url.startswith("https://")
