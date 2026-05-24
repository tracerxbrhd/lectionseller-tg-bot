from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SectionDTO:
    id: int
    title: str
    description: str | None


@dataclass(frozen=True, slots=True)
class BlockDTO:
    id: int
    section_id: int
    title: str
    description: str | None
    price: Decimal


@dataclass(frozen=True, slots=True)
class LectureDTO:
    id: int
    block_id: int
    title: str
    short_description: str | None
    full_description: str | None
    price: Decimal

