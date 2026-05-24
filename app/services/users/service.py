from __future__ import annotations

from app.db.models import User
from app.db.repositories.users import UserRepository
from app.services.users.dto import TelegramUserData


class UserService:
    def __init__(self, repository: UserRepository, admin_telegram_ids: list[int]) -> None:
        self._repository = repository
        self._admin_telegram_ids = admin_telegram_ids

    async def register_or_update_from_telegram(self, data: TelegramUserData) -> User:
        return await self._repository.upsert_telegram_user(
            telegram_id=data.telegram_id,
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            is_admin=data.telegram_id in self._admin_telegram_ids,
        )

