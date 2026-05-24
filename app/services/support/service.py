from __future__ import annotations

from app.db.models import SupportRequest
from app.db.repositories import SupportRepository
from app.services.support.dto import SupportRequestDTO


class SupportRequestError(Exception):
    """Raised when a support request cannot be created."""


class SupportService:
    MIN_MESSAGE_LENGTH = 5
    MAX_MESSAGE_LENGTH = 4000

    def __init__(self, repository: SupportRepository) -> None:
        self._repository = repository

    async def create_request(self, *, user_id: int, message: str) -> SupportRequestDTO:
        normalized_message = message.strip()
        if len(normalized_message) < self.MIN_MESSAGE_LENGTH:
            raise SupportRequestError("Support message is too short.")
        if len(normalized_message) > self.MAX_MESSAGE_LENGTH:
            raise SupportRequestError("Support message is too long.")

        request = await self._repository.create(
            user_id=user_id,
            message=normalized_message,
        )
        return self._to_dto(request)

    @staticmethod
    def _to_dto(request: SupportRequest) -> SupportRequestDTO:
        return SupportRequestDTO(
            id=request.id,
            user_id=request.user_id,
            message=request.message,
            status=request.status,
            created_at=request.created_at,
        )
