from __future__ import annotations

from datetime import datetime

from app.db.models import AccessGrant, ContentItem, Lecture, Purchase
from app.db.repositories import AccessRepository, CatalogRepository
from app.services.content.dto import ContentItemDTO, PurchasedLectureDTO


class ContentAccessError(Exception):
    """Raised when a user has no access to requested content."""


class ContentLibraryService:
    def __init__(
        self,
        *,
        access_repository: AccessRepository,
        catalog_repository: CatalogRepository,
    ) -> None:
        self._access_repository = access_repository
        self._catalog_repository = catalog_repository

    async def list_purchased_lectures(self, user_id: int) -> list[PurchasedLectureDTO]:
        rows = await self._access_repository.list_active_lecture_accesses(user_id=user_id)
        lectures_by_id: dict[int, PurchasedLectureDTO] = {}
        for lecture, grant, purchase in rows:
            if lecture.id in lectures_by_id:
                continue
            lectures_by_id[lecture.id] = self._purchased_lecture_to_dto(
                lecture,
                grant,
                purchase,
            )
        return list(lectures_by_id.values())

    async def get_purchased_lecture(
        self,
        *,
        user_id: int,
        lecture_id: int,
    ) -> PurchasedLectureDTO:
        rows = await self._access_repository.list_active_lecture_accesses(user_id=user_id)
        for lecture, grant, purchase in rows:
            if lecture.id == lecture_id:
                return self._purchased_lecture_to_dto(lecture, grant, purchase)
        raise ContentAccessError("Lecture is not available for this user.")

    async def list_lecture_content(
        self,
        *,
        user_id: int,
        lecture_id: int,
    ) -> list[ContentItemDTO]:
        if not await self._access_repository.has_active_access(
            user_id=user_id,
            lecture_id=lecture_id,
        ):
            raise ContentAccessError("Lecture is not available for this user.")

        return [
            self._content_item_to_dto(item)
            for item in await self._catalog_repository.list_content_items(lecture_id)
        ]

    async def get_content_item(
        self,
        *,
        user_id: int,
        content_item_id: int,
    ) -> ContentItemDTO:
        item = await self._catalog_repository.get_content_item(content_item_id)
        if item is None:
            raise ContentAccessError("Content item is not available.")

        if not await self._access_repository.has_active_access(
            user_id=user_id,
            lecture_id=item.lecture_id,
        ):
            raise ContentAccessError("Content item is not available for this user.")

        return self._content_item_to_dto(item)

    @staticmethod
    def _purchased_lecture_to_dto(
        lecture: Lecture,
        grant: AccessGrant,
        purchase: Purchase | None,
    ) -> PurchasedLectureDTO:
        purchased_at = _purchase_date(purchase, grant.granted_at)
        return PurchasedLectureDTO(
            id=lecture.id,
            title=lecture.title,
            short_description=lecture.short_description,
            purchased_at=purchased_at,
            source_purchase_id=grant.source_purchase_id,
        )

    @staticmethod
    def _content_item_to_dto(item: ContentItem) -> ContentItemDTO:
        return ContentItemDTO(
            id=item.id,
            lecture_id=item.lecture_id,
            type=item.type,
            title=item.title,
            file_path=item.file_path,
            telegram_file_id=item.telegram_file_id,
            text_content=item.text_content,
            protected_content_enabled=item.protected_content_enabled,
        )


def _purchase_date(purchase: Purchase | None, fallback: datetime) -> datetime:
    if purchase is None:
        return fallback
    return purchase.paid_at or purchase.created_at or fallback
