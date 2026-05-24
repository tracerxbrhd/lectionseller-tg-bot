from __future__ import annotations

from app.common.enums import PurchaseStatus, PurchaseType
from app.db.models import AccessGrant, Purchase
from app.db.repositories import AccessRepository, CatalogRepository, PurchaseRepository


class AccessGrantError(Exception):
    """Raised when access cannot be granted for a purchase."""


class AccessService:
    def __init__(
        self,
        *,
        access_repository: AccessRepository,
        purchase_repository: PurchaseRepository,
        catalog_repository: CatalogRepository,
    ) -> None:
        self._access_repository = access_repository
        self._purchase_repository = purchase_repository
        self._catalog_repository = catalog_repository

    async def grant_for_paid_purchase(self, purchase_id: int) -> list[AccessGrant]:
        purchase = await self._purchase_repository.get(purchase_id)
        if purchase is None:
            raise AccessGrantError("Purchase not found.")
        if purchase.status != PurchaseStatus.PAID:
            raise AccessGrantError("Purchase must be paid before granting access.")

        lecture_ids = await self._resolve_lecture_ids(purchase)
        grants: list[AccessGrant] = []
        for lecture_id in lecture_ids:
            existing = await self._access_repository.get_by_purchase_and_lecture(
                source_purchase_id=purchase.id,
                lecture_id=lecture_id,
                user_id=purchase.user_id,
            )
            if existing is not None:
                grants.append(existing)
                continue

            grants.append(
                await self._access_repository.create_grant(
                    user_id=purchase.user_id,
                    lecture_id=lecture_id,
                    source_purchase_id=purchase.id,
                ),
            )

        return grants

    async def has_active_access(self, *, user_id: int, lecture_id: int) -> bool:
        return await self._access_repository.has_active_access(user_id=user_id, lecture_id=lecture_id)

    async def _resolve_lecture_ids(self, purchase: Purchase) -> list[int]:
        if purchase.purchase_type == PurchaseType.LECTURE:
            lecture = await self._catalog_repository.get_lecture(purchase.object_id)
            if lecture is None:
                raise AccessGrantError("Lecture is not available.")
            return [lecture.id]

        if purchase.purchase_type == PurchaseType.BLOCK:
            block = await self._catalog_repository.get_block(purchase.object_id)
            if block is None:
                raise AccessGrantError("Block is not available.")
            lectures = await self._catalog_repository.list_lectures(block.id)
            return [lecture.id for lecture in lectures]

        if purchase.purchase_type == PurchaseType.SECTION:
            section = await self._catalog_repository.get_section(purchase.object_id)
            if section is None:
                raise AccessGrantError("Section is not available.")
            lecture_ids: list[int] = []
            for block in await self._catalog_repository.list_blocks(section.id):
                lecture_ids.extend(
                    lecture.id for lecture in await self._catalog_repository.list_lectures(block.id)
                )
            return lecture_ids

        raise AccessGrantError("Unsupported purchase type.")

