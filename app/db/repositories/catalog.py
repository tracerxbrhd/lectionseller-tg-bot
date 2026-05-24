from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Block, ContentItem, Lecture, Section


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_sections(self) -> list[Section]:
        result = await self._session.execute(
            select(Section)
            .where(Section.is_active.is_(True))
            .order_by(Section.sort_order, Section.id),
        )
        return list(result.scalars().all())

    async def get_section(self, section_id: int) -> Section | None:
        result = await self._session.execute(
            select(Section).where(
                Section.id == section_id,
                Section.is_active.is_(True),
            ),
        )
        return result.scalar_one_or_none()

    async def list_blocks(self, section_id: int) -> list[Block]:
        result = await self._session.execute(
            select(Block)
            .where(
                Block.section_id == section_id,
                Block.is_active.is_(True),
            )
            .order_by(Block.sort_order, Block.id),
        )
        return list(result.scalars().all())

    async def get_block(self, block_id: int) -> Block | None:
        result = await self._session.execute(
            select(Block)
            .join(Section)
            .where(
                Block.id == block_id,
                Block.is_active.is_(True),
                Section.is_active.is_(True),
            ),
        )
        return result.scalar_one_or_none()

    async def list_lectures(self, block_id: int) -> list[Lecture]:
        result = await self._session.execute(
            select(Lecture)
            .where(
                Lecture.block_id == block_id,
                Lecture.is_active.is_(True),
            )
            .order_by(Lecture.sort_order, Lecture.id),
        )
        return list(result.scalars().all())

    async def get_lecture(self, lecture_id: int) -> Lecture | None:
        result = await self._session.execute(
            select(Lecture)
            .join(Block)
            .join(Section)
            .where(
                Lecture.id == lecture_id,
                Lecture.is_active.is_(True),
                Block.is_active.is_(True),
                Section.is_active.is_(True),
            ),
        )
        return result.scalar_one_or_none()

    async def list_content_items(self, lecture_id: int) -> list[ContentItem]:
        result = await self._session.execute(
            select(ContentItem)
            .where(ContentItem.lecture_id == lecture_id)
            .order_by(ContentItem.sort_order, ContentItem.id),
        )
        return list(result.scalars().all())

    async def get_content_item(self, content_item_id: int) -> ContentItem | None:
        result = await self._session.execute(
            select(ContentItem)
            .join(Lecture)
            .join(Block)
            .join(Section)
            .where(
                ContentItem.id == content_item_id,
                Lecture.is_active.is_(True),
                Block.is_active.is_(True),
                Section.is_active.is_(True),
            ),
        )
        return result.scalar_one_or_none()
