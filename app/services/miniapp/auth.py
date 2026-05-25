from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class MiniAppAuthError(Exception):
    """Raised when Telegram Mini App initData cannot be trusted."""


@dataclass(frozen=True, slots=True)
class TelegramMiniAppUser:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    auth_date: int


class MiniAppAuthService:
    def __init__(
        self,
        *,
        bot_token: str,
        max_age_seconds: int,
        now: int | None = None,
    ) -> None:
        self._bot_token = bot_token
        self._max_age_seconds = max_age_seconds
        self._now = now

    def validate_init_data(self, init_data: str) -> TelegramMiniAppUser:
        payload = self._parse_init_data(init_data)
        received_hash = payload.pop("hash", None)
        if not received_hash:
            raise MiniAppAuthError("Telegram initData hash is missing.")

        data_check_string = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
        secret_key = hmac.new(
            b"WebAppData",
            self._bot_token.encode(),
            hashlib.sha256,
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            raise MiniAppAuthError("Telegram initData signature is invalid.")

        auth_date = self._parse_auth_date(payload.get("auth_date"))
        self._validate_freshness(auth_date)

        return self._parse_user(payload.get("user"), auth_date)

    @staticmethod
    def _parse_init_data(init_data: str) -> dict[str, str]:
        if not init_data:
            raise MiniAppAuthError("Telegram initData is missing.")

        try:
            pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise MiniAppAuthError("Telegram initData query string is invalid.") from exc

        payload: dict[str, str] = {}
        for key, value in pairs:
            if not key:
                raise MiniAppAuthError("Telegram initData contains an empty key.")
            if key in payload:
                raise MiniAppAuthError("Telegram initData contains duplicate keys.")
            payload[key] = value

        return payload

    @staticmethod
    def _parse_auth_date(value: str | None) -> int:
        if value is None:
            raise MiniAppAuthError("Telegram initData auth_date is missing.")
        try:
            auth_date = int(value)
        except ValueError as exc:
            raise MiniAppAuthError("Telegram initData auth_date is invalid.") from exc
        if auth_date <= 0:
            raise MiniAppAuthError("Telegram initData auth_date is invalid.")
        return auth_date

    def _validate_freshness(self, auth_date: int) -> None:
        if self._max_age_seconds <= 0:
            return

        now = self._now if self._now is not None else int(time.time())
        if auth_date > now + 60:
            raise MiniAppAuthError("Telegram initData auth_date is from the future.")
        if now - auth_date > self._max_age_seconds:
            raise MiniAppAuthError("Telegram initData is expired.")

    @staticmethod
    def _parse_user(user_payload: str | None, auth_date: int) -> TelegramMiniAppUser:
        if user_payload is None:
            raise MiniAppAuthError("Telegram initData user payload is missing.")

        try:
            user_data = json.loads(user_payload)
        except json.JSONDecodeError as exc:
            raise MiniAppAuthError("Telegram initData user payload is invalid JSON.") from exc

        if not isinstance(user_data, dict):
            raise MiniAppAuthError("Telegram initData user payload is invalid.")

        telegram_id = user_data.get("id")
        if type(telegram_id) is not int:
            raise MiniAppAuthError("Telegram initData user id is invalid.")

        return TelegramMiniAppUser(
            telegram_id=telegram_id,
            username=_optional_str(user_data.get("username")),
            first_name=_optional_str(user_data.get("first_name")),
            last_name=_optional_str(user_data.get("last_name")),
            auth_date=auth_date,
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None
