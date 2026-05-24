from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.common.enums import SupportRequestStatus


@dataclass(frozen=True, slots=True)
class SupportRequestDTO:
    id: int
    user_id: int
    message: str
    status: SupportRequestStatus
    created_at: datetime
