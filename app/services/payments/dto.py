from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.common.enums import PaymentProvider, PaymentStatus


@dataclass(frozen=True, slots=True)
class ProviderPayment:
    provider: PaymentProvider
    provider_payment_id: str
    amount: Decimal
    status: PaymentStatus
    confirmation_url: str | None
    metadata: dict[str, str]
    raw_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class WebhookProcessingResult:
    provider_payment_id: str
    event: str
    handled: bool
    purchase_id: int | None = None
    granted_count: int = 0


@dataclass(frozen=True, slots=True)
class PaymentConfirmationResult:
    provider_payment_id: str
    status: PaymentStatus
    handled: bool
    purchase_id: int | None = None
    granted_count: int = 0
