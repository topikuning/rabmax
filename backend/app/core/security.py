"""Security primitives: password hashing (bcrypt) + JWT HS256 (stdlib).

Sengaja TIDAK pakai PyJWT/`cryptography` — HS256 cukup dengan hmac+hashlib stdlib,
menghindari dependency native yang rapuh. bcrypt dipakai untuk hashing password
(standar industri; tersedia wheel di python:3.12-slim Railway).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import bcrypt

from app.config import settings

ALGORITHM = "HS256"
_BCRYPT_MAX_BYTES = 72  # batas bcrypt; truncate aman.


class TokenError(Exception):
    """Token tidak valid / kadaluarsa / signature salah."""


# --- Password hashing ---


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT HS256 (stdlib) ---


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def _sign(signing_input: bytes) -> bytes:
    return hmac.new(
        settings.secret_key.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    now = int(time.time())
    exp = now + (expires_minutes or settings.access_token_expire_minutes) * 60
    header = {"alg": ALGORITHM, "typ": "JWT"}
    payload = {"sub": str(subject), "iat": now, "exp": exp}
    seg = (
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        + "."
        + _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    )
    sig = _b64url_encode(_sign(seg.encode("ascii")))
    return f"{seg}.{sig}"


def decode_access_token(token: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError as e:
        raise TokenError("Format token tidak valid") from e

    expected = _sign(f"{header_b64}.{payload_b64}".encode("ascii"))
    try:
        actual = _b64url_decode(sig_b64)
    except Exception as e:  # noqa: BLE001
        raise TokenError("Signature tidak bisa di-decode") from e
    if not hmac.compare_digest(expected, actual):
        raise TokenError("Signature tidak cocok")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:  # noqa: BLE001
        raise TokenError("Payload tidak bisa di-decode") from e

    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Token kadaluarsa")
    return payload
