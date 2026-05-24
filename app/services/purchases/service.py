from __future__ import annotations

from decimal import Decimal

from app.common.enums import PurchaseType
from app.db.models import Block, Lecture, Purchase, Section
from app.db.repositories import CatalogRepository, PurchaseRepository
from app.services.purchases.dto import PurchaseDTO


class PurchaseError(Exception):
    """Raised when a purchase cannot be created."""


class PurchaseService:
    def __init__(
        self,
        *,
        purchase_repository: PurchaseRepository,
        catalog_repository: CatalogRepository,
    ) -> None:
        self._purchase_repository = purchase_repository
        self._catalog_repository = catalog_repository

    async def create_pending_purchase(
        self,
        *,
        user_id: int,
        purchase_type: PurchaseType,
        object_id: int,
    ) -> PurchaseDTO:
        item = await self._get_purchasable_item(purchase_type, object_id)
        price = self._get_item_price(item)

        existing = await self._purchase_repository.get_latest_pending_for_object(
            user_id=user_id,
            purchase_type=purchase_type,
            object_id=object_id,
        )
        if existing is not None:
            return self._to_dto(existing)

        purchase = await self._purchase_repository.create_pending(
            user_id=user_id,
            purchase_type=purchase_type,
            object_id=object_id,
            price=price,
        )
        return self._to_dto(purchase)

    async def _get_purchasable_item(
        self,
        purchase_type: PurchaseType,
        object_id: int,
    ) -> Lecture | Block | Section:
        if purchase_type == PurchaseType.LECTURE:
            lecture = await self._catalog_repository.get_lecture(object_id)
            if lecture is None:
                raise PurchaseError("Lecture is not available.")
            return lecture

        if purchase_type == PurchaseType.BLOCK:
            block = await self._catalog_repository.get_block(object_id)
            if block is None:
                raise PurchaseError("Block is not available.")
            return block

        if purchase_type == PurchaseType.SECTION:
            section = await self._catalog_repository.get_section(object_id)
            if section is None:
                raise PurchaseError("Section is not available.")
            return section

        raise PurchaseError("Unsupported purchase type.")

    @staticmethod
    def _get_item_price(item: Lecture | Block | Section) -> Decimal:
        if isinstance(item, Section):
            raise PurchaseError("Section purchases are not enabled yet.")
        return item.price

    @staticmethod
    def _to_dto(purchase: Purchase) -> PurchaseDTO:
        return PurchaseDTO(
            id=purchase.id,
            user_id=purchase.user_id,
            purchase_type=purchase.purchase_type,
            object_id=purchase.object_id,
            price=purchase.price,
            status=purchase.status,
            created_at=purchase.created_at,
        )

