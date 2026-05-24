from __future__ import annotations

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
