from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.services.miniapp import MiniAppAuthError, MiniAppAuthService


BOT_TOKEN = "123456:test-token"


def test_validate_init_data_accepts_valid_payload() -> None:
    init_data = _build_init_data(auth_date=1_700_000_000)

    user = MiniAppAuthService(
        bot_token=BOT_TOKEN,
        max_age_seconds=3600,
        now=1_700_000_100,
    ).validate_init_data(init_data)

    assert user.telegram_id == 42
    assert user.username == "student"
    assert user.first_name == "Test"
    assert user.last_name == "User"


def test_validate_init_data_rejects_invalid_hash() -> None:
    init_data = _build_init_data(auth_date=1_700_000_000).replace("hash=", "hash=bad")

    with pytest.raises(MiniAppAuthError):
        MiniAppAuthService(
            bot_token=BOT_TOKEN,
            max_age_seconds=3600,
            now=1_700_000_100,
        ).validate_init_data(init_data)


def test_validate_init_data_rejects_expired_payload() -> None:
    init_data = _build_init_data(auth_date=1_700_000_000)

    with pytest.raises(MiniAppAuthError):
        MiniAppAuthService(
            bot_token=BOT_TOKEN,
            max_age_seconds=60,
            now=1_700_000_100,
        ).validate_init_data(init_data)


def _build_init_data(*, auth_date: int) -> str:
    payload = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {
                "id": 42,
                "first_name": "Test",
                "last_name": "User",
                "username": "student",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={payload[key]}" for key in sorted(payload))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(payload)
