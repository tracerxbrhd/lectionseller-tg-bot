from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.constants import SUPPORT_CANCEL


def build_support_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SUPPORT_CANCEL)]],
        resize_keyboard=True,
        input_field_placeholder="Напишите вопрос",
    )
