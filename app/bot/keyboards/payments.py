from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


PAYMENT_CHECK_PREFIX = "payment:check"


def payment_check_callback(purchase_id: int) -> str:
    return f"{PAYMENT_CHECK_PREFIX}:{purchase_id}"


def build_payment_keyboard(confirmation_url: str, purchase_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Перейти к оплате", url=confirmation_url)],
            [
                InlineKeyboardButton(
                    text="Проверить статус оплаты",
                    callback_data=payment_check_callback(purchase_id),
                ),
            ],
        ],
    )
