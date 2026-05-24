from __future__ import annotations

from typing import Any

from app.common.logging import get_logger
from app.services.payments.base import PaymentWebhookError
from app.services.payments.confirmation import (
    PaymentConfirmationError,
    PaymentConfirmationService,
)
from app.services.payments.dto import WebhookProcessingResult


logger = get_logger(__name__)


class YooKassaWebhookService:
    def __init__(
        self,
        *,
        confirmation_service: PaymentConfirmationService,
    ) -> None:
        self._confirmation_service = confirmation_service

    async def process(self, payload: dict[str, Any]) -> WebhookProcessingResult:
        event = self._extract_event(payload)
        provider_payment_id = self._extract_provider_payment_id(payload)
        try:
            result = await self._confirmation_service.confirm_by_provider_payment_id(
                provider_payment_id=provider_payment_id,
                raw_context={"webhook": payload},
            )
        except PaymentConfirmationError as exc:
            raise PaymentWebhookError("YooKassa payment confirmation failed.") from exc

        if not result.handled:
            logger.warning(
                "YooKassa webhook ignored: local payment not found for provider id %s",
                provider_payment_id,
            )

        return WebhookProcessingResult(
            provider_payment_id=provider_payment_id,
            event=event,
            handled=result.handled,
            purchase_id=result.purchase_id,
            granted_count=result.granted_count,
        )

    @staticmethod
    def _extract_event(payload: dict[str, Any]) -> str:
        event = payload.get("event")
        if not isinstance(event, str) or not event:
            raise PaymentWebhookError("YooKassa webhook event is missing.")
        return event

    @staticmethod
    def _extract_provider_payment_id(payload: dict[str, Any]) -> str:
        payment_object = payload.get("object")
        if not isinstance(payment_object, dict):
            raise PaymentWebhookError("YooKassa webhook object is missing.")

        provider_payment_id = payment_object.get("id")
        if not isinstance(provider_payment_id, str) or not provider_payment_id:
            raise PaymentWebhookError("YooKassa webhook payment id is missing.")
        return provider_payment_id
