from __future__ import annotations

from ipaddress import ip_address, ip_network
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.logging import get_logger
from app.config.settings import Settings, get_settings
from app.db.repositories import (
    AccessRepository,
    CatalogRepository,
    PaymentRepository,
    PurchaseRepository,
)
from app.services.access import AccessService
from app.services.payments import (
    PaymentConfigurationError,
    PaymentConfirmationService,
    PaymentProviderError,
    PaymentWebhookError,
    YooKassaPaymentService,
    YooKassaWebhookService,
)
from app.web.dependencies import get_db_session


router = APIRouter(prefix="/payments", tags=["payments"])
logger = get_logger(__name__)


@router.get("/return", response_class=HTMLResponse)
async def payment_return() -> str:
    return (
        "<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
        "<title>Оплата</title></head><body>"
        "<h1>Спасибо</h1>"
        "<p>Вернитесь в Telegram-бота. "
        "После подтверждения оплаты доступ появится автоматически.</p>"
        "</body></html>"
    )


@router.post("/webhooks/yookassa")
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    settings = get_settings()
    _validate_source_ip(request, settings)
    payload = await _read_json_payload(request)

    purchase_repository = PurchaseRepository(session)
    catalog_repository = CatalogRepository(session)
    confirmation_service = PaymentConfirmationService(
        payment_repository=PaymentRepository(session),
        purchase_repository=purchase_repository,
        access_service=AccessService(
            access_repository=AccessRepository(session),
            purchase_repository=purchase_repository,
            catalog_repository=catalog_repository,
        ),
        payment_service=YooKassaPaymentService(settings),
    )
    service = YooKassaWebhookService(confirmation_service=confirmation_service)

    try:
        result = await service.process(payload)
    except PaymentWebhookError as exc:
        logger.warning("Rejected YooKassa webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YooKassa webhook.",
        ) from exc
    except PaymentConfigurationError as exc:
        logger.exception("YooKassa webhook cannot be processed: provider is not configured.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider is not configured.",
        ) from exc
    except PaymentProviderError as exc:
        logger.exception("YooKassa webhook provider verification failed.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment provider verification failed.",
        ) from exc

    return {
        "status": "ok",
        "handled": result.handled,
        "event": result.event,
        "purchase_id": result.purchase_id,
        "granted_count": result.granted_count,
    }


async def _read_json_payload(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="JSON object payload is required.",
        )
    return payload


def _validate_source_ip(request: Request, settings: Settings) -> None:
    allowed_networks = settings.yookassa_webhook_allowed_ip_list
    if not allowed_networks:
        return

    client_host = request.client.host if request.client is not None else ""
    try:
        client_ip = ip_address(client_host)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook source IP is not allowed.",
        ) from exc

    try:
        is_allowed = any(
            client_ip in ip_network(network, strict=False)
            for network in allowed_networks
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook IP allowlist is invalid.",
        ) from exc

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook source IP is not allowed.",
        )
