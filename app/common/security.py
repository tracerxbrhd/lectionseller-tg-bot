from __future__ import annotations

import base64
import hashlib
import hmac
import time

from passlib.context import CryptContext


_PASSWORD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return _PASSWORD_CONTEXT.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _PASSWORD_CONTEXT.verify(password, password_hash)


def create_signed_admin_session(*, admin_id: int, secret: str, ttl_seconds: int) -> str:
    expires_at = int(time.time()) + ttl_seconds
    payload = f"{admin_id}:{expires_at}"
    signature = _sign(payload, secret)
    token = f"{payload}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("ascii")


def verify_signed_admin_session(token: str, *, secret: str) -> int | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        raw_admin_id, raw_expires_at, signature = decoded.split(":", maxsplit=2)
        payload = f"{raw_admin_id}:{raw_expires_at}"
        expected_signature = _sign(payload, secret)
        expires_at = int(raw_expires_at)
        admin_id = int(raw_admin_id)
    except (ValueError, UnicodeDecodeError):
        return None

    if not hmac.compare_digest(signature, expected_signature):
        return None
    if expires_at < int(time.time()):
        return None
    return admin_id


def _sign(payload: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
