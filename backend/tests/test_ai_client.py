"""Unit test ketahanan AI client: unwrap error, non-retryable, circuit-breaker."""

import pytest
from tenacity import RetryError

import app.ai.client as ai
from app.ai.client import AIClient, AIMessage, _explain, _http_status, _is_retryable, _root_cause


class _SDKError(Exception):
    def __init__(self, status, msg="err"):
        self.status_code = status
        self.message = msg
        super().__init__(msg)


def test_http_status_and_retryable():
    assert _http_status(_SDKError(401)) == 401
    assert _is_retryable(_SDKError(401)) is False   # auth → jangan retry
    assert _is_retryable(_SDKError(422)) is False   # validasi → jangan retry
    assert _is_retryable(_SDKError(429)) is True    # rate limit → boleh retry
    assert _is_retryable(_SDKError(500)) is True
    assert _is_retryable(RuntimeError("network")) is True  # tanpa status → retry


def test_root_cause_unwraps_retryerror():
    inner = _SDKError(401, "Unauthorized")
    try:
        raise inner
    except Exception:
        from tenacity import Future
        fut = Future(1)
        fut.set_exception(inner)
        wrapped = RetryError(fut)
    assert _root_cause(wrapped) is inner
    assert "HTTP 401" in _explain(wrapped)


@pytest.mark.asyncio
async def test_circuit_breaker_disables_provider_on_auth_fail(monkeypatch):
    """Provider yang gagal 401 di-disable → call kedua langsung gagal tanpa retry/network."""
    monkeypatch.setattr(ai, "_configured", lambda p: p == "mistral")
    monkeypatch.setattr(ai.settings, "default_ai_provider", "mistral")
    monkeypatch.setattr(ai.settings, "ai_fallback_order", ["mistral"])

    client = AIClient()
    calls = {"n": 0}

    async def _boom(messages, model, max_tokens, temperature):
        calls["n"] += 1
        raise _SDKError(401, "Unauthorized")

    monkeypatch.setattr(client, "_call_mistral", _boom)
    msgs = [AIMessage(role="user", content="hi")]

    with pytest.raises(RuntimeError):
        await client.complete(msgs)
    assert calls["n"] == 1
    assert "mistral" in client._disabled

    # Call kedua: provider sudah di-disable → tak memanggil _call_mistral lagi.
    with pytest.raises(RuntimeError, match="dimatikan|dipakai"):
        await client.complete(msgs)
    assert calls["n"] == 1  # tidak bertambah


@pytest.mark.asyncio
async def test_circuit_breaker_disables_after_consecutive_failures(monkeypatch):
    """Error non-auth (mis. 429) yang terus-menerus → provider mati setelah N gagal."""
    monkeypatch.setattr(ai, "_configured", lambda p: p == "mistral")
    monkeypatch.setattr(ai.settings, "default_ai_provider", "mistral")
    monkeypatch.setattr(ai.settings, "ai_fallback_order", ["mistral"])

    client = AIClient()
    calls = {"n": 0}

    async def _rate_limited(messages, model, max_tokens, temperature):
        calls["n"] += 1
        raise _SDKError(429, "rate limited")  # bukan auth → retryable, tapi terus gagal

    monkeypatch.setattr(client, "_call_mistral", _rate_limited)
    msgs = [AIMessage(role="user", content="hi")]

    # 3 panggilan pertama mencoba API; panggilan ke-3 mencapai ambang & disable.
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await client.complete(msgs)
    assert "mistral" in client._disabled
    assert calls["n"] == 3

    # Panggilan ke-4: provider sudah mati → tak ada call API lagi (matcher lanjut cepat).
    with pytest.raises(RuntimeError):
        await client.complete(msgs)
    assert calls["n"] == 3
