from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main_menu import build_main_menu_keyboard
from app.bot.keyboards.payments import PAYMENT_CHECK_PREFIX
from app.common.enums import PaymentStatus
from app.common.logging import get_logger
from app.config.settings import get_settings
from app.db.models import User
from app.db.repositories import (
    AccessRepository,
    CatalogRepository,
    PaymentRepository,
    PurchaseRepository,
    UserRepository,
)
from app.services.access import AccessService
from app.services.payments import (
    PaymentConfigurationError,
    PaymentConfirmationError,
    PaymentConfirmationResult,
    PaymentConfirmationService,
    PaymentProviderError,
    YooKassaPaymentService,
)
from app.services.users import TelegramUserData, UserService


router = Router(name="payments")
logger = get_logger(__name__)


@router.callback_query(F.data.startswith(f"{PAYMENT_CHECK_PREFIX}:"))
async def check_payment(callback: CallbackQuery, session: AsyncSession) -> None:
    purchase_id = _last_int(callback.data)
    if purchase_id is None:
        await callback.answer("Покупка не найдена.", show_alert=True)
        return

    user = await _ensure_user(callback, session)
    service = _confirmation_service(session)

    try:
        result = await service.confirm_by_purchase_id(
            purchase_id=purchase_id,
            user_id=user.id,
            raw_context={"manual_check": {"telegram_id": callback.from_user.id}},
        )
    except PaymentConfigurationError:
        logger.exception("Could not check payment %s: YooKassa is not configured.", purchase_id)
        await callback.answer("Проверка оплаты сейчас недоступна.", show_alert=True)
        return
    except PaymentProviderError:
        await callback.answer("YooKassa временно не ответила. Попробуйте позже.", show_alert=True)
        return
    except PaymentConfirmationError:
        logger.exception("Could not confirm payment for purchase %s.", purchase_id)
        await callback.answer("Не удалось проверить эту оплату.", show_alert=True)
        return

    await _answer_payment_check(callback, result)


def _confirmation_service(session: AsyncSession) -> PaymentConfirmationService:
    purchase_repository = PurchaseRepository(session)
    catalog_repository = CatalogRepository(session)
    return PaymentConfirmationService(
        payment_repository=PaymentRepository(session),
        purchase_repository=purchase_repository,
        access_service=AccessService(
            access_repository=AccessRepository(session),
            purchase_repository=purchase_repository,
            catalog_repository=catalog_repository,
        ),
        payment_service=YooKassaPaymentService(get_settings()),
    )


async def _ensure_user(callback: CallbackQuery, session: AsyncSession) -> User:
    telegram_user = callback.from_user
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


async def _answer_payment_check(
    callback: CallbackQuery,
    result: PaymentConfirmationResult,
) -> None:
    if result.status == PaymentStatus.SUCCEEDED:
        await callback.answer("Оплата подтверждена, доступ открыт.", show_alert=True)
        if callback.message is not None:
            await callback.message.answer(
                "<b>Статус оплаты:</b> <code>ПОДТВЕРЖДЕНА</code>\n\n"
                "Доступ открыт. Материалы уже доступны в разделе «Мои покупки».",
                reply_markup=build_main_menu_keyboard(),
            )
        return

    if result.status in {PaymentStatus.PENDING, PaymentStatus.WAITING_FOR_CAPTURE}:
        await callback.answer(
            "Платеж еще обрабатывается. Проверьте статус чуть позже.",
            show_alert=True,
        )
        if callback.message is not None:
            await callback.message.answer(
                "<b>Статус оплаты:</b> <code>ОБРАБАТЫВАЕТСЯ</code>\n\n"
                "YooKassa еще не подтвердила платеж. Обычно это занимает несколько секунд. "
                "Нажмите «Проверить статус оплаты» повторно чуть позже.",
            )
        return

    if result.status == PaymentStatus.CANCELED:
        await callback.answer("Платёж отменён.", show_alert=True)
        if callback.message is not None:
            await callback.message.answer(
                "<b>Статус оплаты:</b> <code>ОТМЕНЕНА</code>\n\n"
                "Платеж отменен. Можно вернуться в каталог и создать новую покупку.",
                reply_markup=build_main_menu_keyboard(),
            )
        return

    await callback.answer("Платёж не прошёл.", show_alert=True)
    if callback.message is not None:
        await callback.message.answer(
            "<b>Статус оплаты:</b> <code>НЕ ПРОШЛА</code>\n\n"
            "Оплата не была подтверждена. Попробуйте создать покупку заново "
            "или напишите в поддержку.",
            reply_markup=build_main_menu_keyboard(),
        )


def _last_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value.rsplit(":", maxsplit=1)[-1])
    except ValueError:
        return None
