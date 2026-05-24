from __future__ import annotations

from abc import ABC, abstractmethod

from app.db.models import Purchase
from app.services.payments.dto import ProviderPayment


class PaymentError(Exception):
    """Base payment processing error."""


class PaymentConfigurationError(PaymentError):
    """Raised when a payment provider is not configured."""


class PaymentProviderError(PaymentError):
    """Raised when a payment provider request fails."""


class PaymentWebhookError(PaymentError):
    """Raised when a payment webhook cannot be trusted or processed."""


class PaymentService(ABC):
    @abstractmethod
    async def create_payment(
        self,
        *,
        purchase: Purchase,
        idempotency_key: str,
    ) -> ProviderPayment:
        raise NotImplementedError

    @abstractmethod
    async def fetch_payment(self, provider_payment_id: str) -> ProviderPayment:
        raise NotImplementedError
