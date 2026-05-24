from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from typing import Any

from yookassa import Configuration
from yookassa import Payment as YooKassaPayment

from app.common.enums import PaymentProvider, PaymentStatus
from app.common.logging import get_logger
from app.config.settings import Settings
from app.db.models import Purchase
from app.services.payments.base import (
    PaymentConfigurationError,
    PaymentProviderError,
    PaymentService,
)
from app.services.payments.dto import ProviderPayment


logger = get_logger(__name__)


class YooKassaPaymentService(PaymentService):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def create_payment(
        self,
        *,
        purchase: Purchase,
        idempotency_key: str,
    ) -> ProviderPayment:
        self._configure()
        payload = self._build_create_payload(purchase)

        try:
            response = await asyncio.to_thread(
                YooKassaPayment.create,
                payload,
                idempotency_key,
            )
        except Exception as exc:
            logger.exception("YooKassa payment creation failed for purchase %s", purchase.id)
            raise PaymentProviderError("YooKassa payment creation failed.") from exc

        return self._provider_payment_from_payload(self._response_to_payload(response))

    async def fetch_payment(self, provider_payment_id: str) -> ProviderPayment:
        self._configure()

        try:
            response = await asyncio.to_thread(YooKassaPayment.find_one, provider_payment_id)
        except Exception as exc:
            logger.exception("YooKassa payment fetch failed for payment %s", provider_payment_id)
            raise PaymentProviderError("YooKassa payment fetch failed.") from exc

        return self._provider_payment_from_payload(self._response_to_payload(response))

    def _configure(self) -> None:
        if not self._settings.yookassa_enabled:
            raise PaymentConfigurationError("YooKassa credentials are not configured.")

        if self._settings.yookassa_secret_key is None:
            raise PaymentConfigurationError("YooKassa secret key is not configured.")

        Configuration.account_id = self._settings.yookassa_shop_id
        Configuration.secret_key = self._settings.yookassa_secret_key.get_secret_value()

    def _build_create_payload(self, purchase: Purchase) -> dict[str, Any]:
        return {
            "amount": {
                "value": self._amount_to_yookassa(purchase.price),
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": self._settings.yookassa_return_url,
            },
            "description": f"Оплата покупки #{purchase.id}",
            "metadata": {
                "purchase_id": str(purchase.id),
                "user_id": str(purchase.user_id),
                "purchase_type": purchase.purchase_type.value,
                "object_id": str(purchase.object_id),
            },
        }

    @staticmethod
    def _provider_payment_from_payload(payload: dict[str, Any]) -> ProviderPayment:
        provider_payment_id = payload.get("id")
        if not isinstance(provider_payment_id, str) or not provider_payment_id:
            raise PaymentProviderError("YooKassa response does not contain payment id.")

        return ProviderPayment(
            provider=PaymentProvider.YOOKASSA,
            provider_payment_id=provider_payment_id,
            amount=_extract_amount(payload),
            status=_status_from_yookassa(payload.get("status")),
            confirmation_url=_extract_confirmation_url(payload),
            metadata=_extract_metadata(payload),
            raw_payload=payload,
        )

    @staticmethod
    def _response_to_payload(response: object) -> dict[str, Any]:
        if isinstance(response, dict):
            return response

        if hasattr(response, "json"):
            raw_json = response.json()
            if isinstance(raw_json, dict):
                return raw_json
            if isinstance(raw_json, bytes):
                return json.loads(raw_json.decode("utf-8"))
            if isinstance(raw_json, str):
                return json.loads(raw_json)

        raise PaymentProviderError("Unsupported YooKassa response format.")

    @staticmethod
    def _amount_to_yookassa(amount: Decimal) -> str:
        return f"{amount.quantize(Decimal('0.01')):.2f}"


def _extract_amount(payload: dict[str, Any]) -> Decimal:
    amount = payload.get("amount")
    if isinstance(amount, dict):
        value = amount.get("value")
        if value is not None:
            return Decimal(str(value)).quantize(Decimal("0.01"))
    return Decimal("0.00")


def _extract_confirmation_url(payload: dict[str, Any]) -> str | None:
    confirmation = payload.get("confirmation")
    if not isinstance(confirmation, dict):
        return None

    confirmation_url = confirmation.get("confirmation_url")
    if isinstance(confirmation_url, str) and confirmation_url:
        return confirmation_url
    return None


def _extract_metadata(payload: dict[str, Any]) -> dict[str, str]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    return {str(key): str(value) for key, value in metadata.items()}


def _status_from_yookassa(value: object) -> PaymentStatus:
    try:
        return PaymentStatus(str(value))
    except ValueError:
        logger.warning("Unknown YooKassa payment status: %r", value)
        return PaymentStatus.FAILED
