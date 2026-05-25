from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import SupportRequestStatus
from app.db.models import SupportRequest


class SupportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        user_id: int,
        message: str,
    ) -> SupportRequest:
        request = SupportRequest(
            user_id=user_id,
            message=message,
            status=SupportRequestStatus.OPEN,
        )
        self._session.add(request)
        await self._session.flush()
        return request

    async def list_by_user(self, user_id: int) -> list[SupportRequest]:
        result = await self._session.execute(
            select(SupportRequest)
            .where(SupportRequest.user_id == user_id)
            .order_by(SupportRequest.created_at.desc(), SupportRequest.id.desc()),
        )
        return list(result.scalars().all())
