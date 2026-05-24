from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AccessGrant, Block, Lecture, Purchase, Section


class AccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active_access(self, *, user_id: int, lecture_id: int) -> bool:
        result = await self._session.execute(
            select(AccessGrant.id)
            .where(
                AccessGrant.user_id == user_id,
                AccessGrant.lecture_id == lecture_id,
                AccessGrant.is_active.is_(True),
                AccessGrant.revoked_at.is_(None),
            )
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def list_active_lecture_accesses(
        self,
        *,
        user_id: int,
    ) -> list[tuple[Lecture, AccessGrant, Purchase | None]]:
        result = await self._session.execute(
            select(Lecture, AccessGrant, Purchase)
            .join(AccessGrant, AccessGrant.lecture_id == Lecture.id)
            .join(Block, Lecture.block_id == Block.id)
            .join(Section, Block.section_id == Section.id)
            .outerjoin(Purchase, AccessGrant.source_purchase_id == Purchase.id)
            .where(
                AccessGrant.user_id == user_id,
                AccessGrant.is_active.is_(True),
                AccessGrant.revoked_at.is_(None),
                Lecture.is_active.is_(True),
                Block.is_active.is_(True),
                Section.is_active.is_(True),
            )
            .order_by(AccessGrant.granted_at.desc(), Lecture.sort_order, Lecture.id),
        )
        return list(result.all())

    async def get_by_purchase_and_lecture(
        self,
        *,
        source_purchase_id: int,
        lecture_id: int,
        user_id: int,
    ) -> AccessGrant | None:
        result = await self._session.execute(
            select(AccessGrant).where(
                AccessGrant.source_purchase_id == source_purchase_id,
                AccessGrant.lecture_id == lecture_id,
                AccessGrant.user_id == user_id,
            ),
        )
        return result.scalar_one_or_none()

    async def create_grant(
        self,
        *,
        user_id: int,
        lecture_id: int,
        source_purchase_id: int | None = None,
        granted_by_admin_id: int | None = None,
    ) -> AccessGrant:
        grant = AccessGrant(
            user_id=user_id,
            lecture_id=lecture_id,
            source_purchase_id=source_purchase_id,
            granted_by_admin_id=granted_by_admin_id,
        )
        self._session.add(grant)
        await self._session.flush()
        return grant
