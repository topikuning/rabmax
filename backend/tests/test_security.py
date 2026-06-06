"""Unit tests auth primitives: bcrypt hashing + stdlib HS256 JWT."""

import time

import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pass")
    assert h != "s3cret-pass"
    assert verify_password("s3cret-pass", h)
    assert not verify_password("wrong", h)


def test_password_hash_unique_salt():
    assert hash_password("same") != hash_password("same")  # salt beda


def test_verify_bad_hash_returns_false():
    assert not verify_password("x", "not-a-bcrypt-hash")


def test_jwt_roundtrip():
    tok = create_access_token(42)
    payload = decode_access_token(tok)
    assert payload["sub"] == "42"
    assert payload["exp"] > payload["iat"]


def test_jwt_tampered_signature():
    tok = create_access_token(1)
    head, body, _sig = tok.split(".")
    forged = f"{head}.{body}.AAAAusupakeganti"
    with pytest.raises(TokenError):
        decode_access_token(forged)


def test_jwt_tampered_payload():
    tok = create_access_token(1)
    head, _body, sig = tok.split(".")
    # ganti payload (sub=999) tanpa re-sign → signature mismatch
    import base64
    import json

    fake = base64.urlsafe_b64encode(
        json.dumps({"sub": "999", "iat": 0, "exp": 9999999999}).encode()
    ).rstrip(b"=").decode()
    with pytest.raises(TokenError):
        decode_access_token(f"{head}.{fake}.{sig}")


def test_jwt_expired():
    tok = create_access_token(1, expires_minutes=-1)  # sudah lewat
    with pytest.raises(TokenError):
        decode_access_token(tok)


def test_jwt_malformed():
    with pytest.raises(TokenError):
        decode_access_token("garbage")
    assert time.time() > 0  # sanity
