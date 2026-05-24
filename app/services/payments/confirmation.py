from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.common.enums import PaymentProvider, PaymentStatus
from app.db.models import Payment
from app.db.repositories import PaymentRepository, PurchaseRepository
from app.services.access import AccessGrantError, AccessService
from app.services.payments.base import PaymentService
from app.services.payments.dto import PaymentConfirmationResult, ProviderPayment


class PaymentConfirmationError(Exception):
    """Raised when a local payment cannot be confirmed safely."""


class PaymentConfirmationService:
    def __init__(
        self,
        *,
        payment_repository: PaymentRepository,
        purchase_repository: PurchaseRepository,
        access_service: AccessService,
        payment_service: PaymentService,
    ) -> None:
        self._payment_repository = payment_repository
        self._purchase_repository = purchase_repository
        self._access_service = access_service
        self._payment_service = payment_service

    async def confirm_by_purchase_id(
        self,
        *,
        purchase_id: int,
        user_id: int | None = None,
        raw_context: dict[str, Any] | None = None,
    ) -> PaymentConfirmationResult:
        purchase = await self._purchase_repository.get(purchase_id)
        if purchase is None:
            raise PaymentConfirmationError("Purchase not found.")
        if user_id is not None and purchase.user_id != user_id:
            raise PaymentConfirmationError("Purchase does not belong to this user.")

        payment = await self._payment_repository.get_by_purchase_id(purchase_id)
        if payment is None:
            raise PaymentConfirmationError("Payment not found.")
        return await self._confirm_payment(payment, raw_context=raw_context)

    async def confirm_by_provider_payment_id(
        self,
        *,
        provider_payment_id: str,
        raw_context: dict[str, Any] | None = None,
    ) -> PaymentConfirmationResult:
        payment = await self._payment_repository.get_by_provider_payment_id(
            provider=PaymentProvider.YOOKASSA,
            provider_payment_id=provider_payment_id,
        )
        if payment is None:
            return PaymentConfirmationResult(
                provider_payment_id=provider_payment_id,
                status=PaymentStatus.FAILED,
                handled=False,
            )
        return await self._confirm_payment(payment, raw_context=raw_context)

    async def _confirm_payment(
        self,
        payment: Payment,
        *,
        raw_context: dict[str, Any] | None,
    ) -> PaymentConfirmationResult:
        provider_payment = await self._payment_service.fetch_payment(payment.provider_payment_id)
        self._validate_provider_payment(payment, provider_payment)

        raw_payload = {"provider_payment": provider_payment.raw_payload}
        if raw_context is not None:
            raw_payload.update(raw_context)

        await self._payment_repository.update_from_provider(
            payment,
            status=provider_payment.status,
            confirmation_url=provider_payment.confirmation_url,
            raw_payload=raw_payload,
        )

        granted_count = 0
        if provider_payment.status == PaymentStatus.SUCCEEDED:
            purchase = await self._purchase_repository.mark_paid(payment.purchase_id)
            if purchase is not None:
                try:
                    grants = await self._access_service.grant_for_paid_purchase(purchase.id)
                except AccessGrantError as exc:
                    raise PaymentConfirmationError(
                        "Could not grant access for paid purchase.",
                    ) from exc
                granted_count = len(grants)
        elif provider_payment.status == PaymentStatus.CANCELED:
            await self._purchase_repository.mark_canceled_if_pending(payment.purchase_id)

        return PaymentConfirmationResult(
            provider_payment_id=provider_payment.provider_payment_id,
            status=provider_payment.status,
            handled=True,
            purchase_id=payment.purchase_id,
            granted_count=granted_count,
        )

    @staticmethod
    def _validate_provider_payment(payment: Payment, provider_payment: ProviderPayment) -> None:
        if payment.provider != provider_payment.provider:
            raise PaymentConfirmationError("Payment provider mismatch.")

        if _normalize_amount(payment.amount) != _normalize_amount(provider_payment.amount):
            raise PaymentConfirmationError("Payment amount mismatch.")

        metadata_purchase_id = provider_payment.metadata.get("purchase_id")
        if metadata_purchase_id and metadata_purchase_id != str(payment.purchase_id):
            raise PaymentConfirmationError("Payment purchase metadata mismatch.")


def _normalize_amount(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"))
