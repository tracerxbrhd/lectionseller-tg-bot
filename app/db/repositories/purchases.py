from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import PurchaseStatus, PurchaseType
from app.db.models import Purchase


class PurchaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, purchase_id: int) -> Purchase | None:
        result = await self._session.execute(
            select(Purchase).where(Purchase.id == purchase_id),
        )
        return result.scalar_one_or_none()

    async def get_latest_pending_for_object(
        self,
        *,
        user_id: int,
        purchase_type: PurchaseType,
        object_id: int,
    ) -> Purchase | None:
        result = await self._session.execute(
            select(Purchase)
            .where(
                Purchase.user_id == user_id,
                Purchase.purchase_type == purchase_type,
                Purchase.object_id == object_id,
                Purchase.status == PurchaseStatus.PENDING,
            )
            .order_by(Purchase.created_at.desc(), Purchase.id.desc()),
        )
        return result.scalars().first()

    async def create_pending(
        self,
        *,
        user_id: int,
        purchase_type: PurchaseType,
        object_id: int,
        price: object,
    ) -> Purchase:
        purchase = Purchase(
            user_id=user_id,
            purchase_type=purchase_type,
            object_id=object_id,
            price=price,
            status=PurchaseStatus.PENDING,
        )
        self._session.add(purchase)
        await self._session.flush()
        return purchase

    async def mark_paid(self, purchase_id: int) -> Purchase | None:
        purchase = await self.get(purchase_id)
        if purchase is None:
            return None

        if purchase.status != PurchaseStatus.PAID:
            purchase.status = PurchaseStatus.PAID
            purchase.paid_at = datetime.now(UTC)
            await self._session.flush()

        return purchase

    async def mark_canceled_if_pending(self, purchase_id: int) -> Purchase | None:
        purchase = await self.get(purchase_id)
        if purchase is None:
            return None

        if purchase.status == PurchaseStatus.PENDING:
            purchase.status = PurchaseStatus.CANCELED
            await self._session.flush()

        return purchase
