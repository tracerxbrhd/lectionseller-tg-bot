from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.db.models import User
from app.db.repositories import UserRepository
from app.services.miniapp import MiniAppAuthError, MiniAppAuthService
from app.web.dependencies import get_db_session


TELEGRAM_INIT_DATA_HEADER = "X-Telegram-Init-Data"


async def require_miniapp_user(
    init_data: Annotated[str | None, Header(alias=TELEGRAM_INIT_DATA_HEADER)] = None,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if settings.bot_token is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot token is not configured.",
        )

    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{TELEGRAM_INIT_DATA_HEADER} header is required.",
        )

    auth_service = MiniAppAuthService(
        bot_token=settings.bot_token.get_secret_value(),
        max_age_seconds=settings.miniapp_init_data_max_age_seconds,
    )
    try:
        telegram_user = auth_service.validate_init_data(init_data)
    except MiniAppAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram Mini App initData is invalid.",
        ) from exc

    user = await UserRepository(session).upsert_telegram_user(
        telegram_id=telegram_user.telegram_id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        is_admin=telegram_user.telegram_id in settings.admin_telegram_id_list,
    )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is blocked.",
        )

    return user


async def require_miniapp_admin(user: User = Depends(require_miniapp_user)) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions are required.",
        )
    return user
