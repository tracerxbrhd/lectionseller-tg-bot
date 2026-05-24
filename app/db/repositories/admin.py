from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminAccount


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, admin_id: int) -> AdminAccount | None:
        result = await self._session.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id),
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> AdminAccount | None:
        result = await self._session.execute(
            select(AdminAccount).where(AdminAccount.username == username),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        username: str,
        password_hash: str,
        is_active: bool = True,
    ) -> AdminAccount:
        admin = AdminAccount(
            username=username,
            password_hash=password_hash,
            is_active=is_active,
        )
        self._session.add(admin)
        await self._session.flush()
        return admin

    async def upsert(
        self,
        *,
        username: str,
        password_hash: str,
        is_active: bool = True,
    ) -> AdminAccount:
        admin = await self.get_by_username(username)
        if admin is None:
            return await self.create(
                username=username,
                password_hash=password_hash,
                is_active=is_active,
            )

        admin.password_hash = password_hash
        admin.is_active = is_active
        await self._session.flush()
        return admin

    async def mark_login(self, admin: AdminAccount) -> None:
        admin.last_login_at = datetime.now(UTC)
        await self._session.flush()
