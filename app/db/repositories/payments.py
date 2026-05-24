from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import PaymentProvider, PaymentStatus
from app.db.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, payment_id: int) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.id == payment_id),
        )
        return result.scalar_one_or_none()

    async def get_by_purchase_id(self, purchase_id: int) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(Payment.purchase_id == purchase_id),
        )
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(
        self,
        *,
        provider: PaymentProvider,
        provider_payment_id: str,
    ) -> Payment | None:
        result = await self._session.execute(
            select(Payment).where(
                Payment.provider == provider,
                Payment.provider_payment_id == provider_payment_id,
            ),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        purchase_id: int,
        provider: PaymentProvider,
        provider_payment_id: str,
        amount: Decimal,
        status: PaymentStatus,
        confirmation_url: str | None,
        raw_payload: dict[str, Any],
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            purchase_id=purchase_id,
            provider=provider,
            provider_payment_id=provider_payment_id,
            amount=amount,
            status=status,
            confirmation_url=confirmation_url,
            raw_payload=raw_payload,
        )
        self._session.add(payment)
        await self._session.flush()
        return payment

    async def update_from_provider(
        self,
        payment: Payment,
        *,
        provider_payment_id: str | None = None,
        status: PaymentStatus | None = None,
        confirmation_url: str | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> Payment:
        if provider_payment_id is not None:
            payment.provider_payment_id = provider_payment_id
        if status is not None:
            payment.status = status
        if confirmation_url is not None:
            payment.confirmation_url = confirmation_url
        if raw_payload is not None:
            payment.raw_payload = raw_payload

        await self._session.flush()
        return payment
