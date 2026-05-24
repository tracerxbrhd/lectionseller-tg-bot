from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.common.enums import ContentType


@dataclass(frozen=True, slots=True)
class PurchasedLectureDTO:
    id: int
    title: str
    short_description: str | None
    purchased_at: datetime
    source_purchase_id: int | None


@dataclass(frozen=True, slots=True)
class ContentItemDTO:
    id: int
    lecture_id: int
    type: ContentType
    title: str
    file_path: str | None
    telegram_file_id: str | None
    text_content: str | None
    protected_content_enabled: bool
