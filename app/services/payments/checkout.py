from __future__ import annotations

from app.common.enums import PaymentStatus
from app.db.models import Payment, Purchase
from app.db.repositories import PaymentRepository
from app.services.payments.base import PaymentService


class CheckoutService:
    def __init__(
        self,
        *,
        payment_repository: PaymentRepository,
        payment_service: PaymentService,
    ) -> None:
        self._payment_repository = payment_repository
        self._payment_service = payment_service

    async def get_or_create_payment(self, purchase: Purchase) -> Payment:
        existing = await self._payment_repository.get_by_purchase_id(purchase.id)
        if existing is not None and self._can_reuse_payment(existing):
            return existing

        provider_payment = await self._payment_service.create_payment(
            purchase=purchase,
            idempotency_key=_purchase_idempotency_key(purchase),
        )

        if existing is not None:
            return await self._payment_repository.update_from_provider(
                existing,
                provider_payment_id=provider_payment.provider_payment_id,
                status=provider_payment.status,
                confirmation_url=provider_payment.confirmation_url,
                raw_payload=provider_payment.raw_payload,
            )

        return await self._payment_repository.create(
            user_id=purchase.user_id,
            purchase_id=purchase.id,
            provider=provider_payment.provider,
            provider_payment_id=provider_payment.provider_payment_id,
            amount=provider_payment.amount,
            status=provider_payment.status,
            confirmation_url=provider_payment.confirmation_url,
            raw_payload=provider_payment.raw_payload,
        )

    @staticmethod
    def _can_reuse_payment(payment: Payment) -> bool:
        reusable_statuses = {
            PaymentStatus.PENDING,
            PaymentStatus.WAITING_FOR_CAPTURE,
            PaymentStatus.SUCCEEDED,
        }
        return payment.status in reusable_statuses and bool(payment.confirmation_url)


def _purchase_idempotency_key(purchase: Purchase) -> str:
    created_at = purchase.created_at.isoformat() if purchase.created_at is not None else "not-set"
    return ":".join(
        (
            "purchase",
            str(purchase.id),
            str(purchase.user_id),
            purchase.purchase_type.value,
            str(purchase.object_id),
            created_at,
        ),
    )
