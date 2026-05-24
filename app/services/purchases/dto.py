from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.common.enums import PurchaseStatus, PurchaseType


@dataclass(frozen=True, slots=True)
class PurchaseDTO:
    id: int
    user_id: int
    purchase_type: PurchaseType
    object_id: int
    price: Decimal
    status: PurchaseStatus
    created_at: datetime

