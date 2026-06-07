"""Multi-provider AI client abstraction.

Supports Claude (Anthropic), Mistral, and OpenAI with automatic fallback.
All providers return same response shape via internal normalization.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Literal

from loguru import logger
from tenacity import (
    RetryError,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

ProviderName = Literal["claude", "mistral", "openai"]

# Status HTTP yang TAK ada gunanya di-retry (gagal permanen → fail-fast).
_NON_RETRYABLE = {400, 401, 403, 404, 405, 422}


def _root_cause(e: BaseException) -> BaseException:
    """Buka bungkus tenacity RetryError → exception asli (SDKError dll)."""
    if isinstance(e, RetryError) and e.last_attempt is not None:
        inner = e.last_attempt.exception()
        if inner is not None:
            return inner
    return e


def _http_status(e: BaseException) -> int | None:
    """Ekstrak status code HTTP dari error SDK (mistralai/anthropic/openai)."""
    for attr in ("status_code", "status", "code"):
        v = getattr(e, attr, None)
        if isinstance(v, int):
            return v
    resp = getattr(e, "response", None)
    sc = getattr(resp, "status_code", None)
    return sc if isinstance(sc, int) else None


def _is_retryable(e: BaseException) -> bool:
    """Retry hanya untuk error transien (timeout/429/5xx); bukan auth/validasi."""
    sc = _http_status(e)
    if sc is None:
        return True  # network/timeout tanpa status → boleh retry
    return sc not in _NON_RETRYABLE


def _explain(e: BaseException) -> str:
    """Pesan error yang informatif (status + isi), bukan 'RetryError[...]'."""
    root = _root_cause(e)
    sc = _http_status(root)
    body = getattr(root, "message", None) or getattr(root, "body", None)
    detail = f"{type(root).__name__}: {root}"
    if sc:
        detail = f"HTTP {sc} — {detail}"
    if body and str(body) not in detail:
        detail += f" | {str(body)[:200]}"
    return detail

_KEY_ATTR = {"claude": "anthropic_api_key", "mistral": "mistral_api_key", "openai": "openai_api_key"}
# (module, kelas client) untuk import-check NYATA (bukan sekadar find_spec).
_IMPORT_CHECK = {
    "claude": ("anthropic", "AsyncAnthropic"),
    "mistral": ("mistralai", "Mistral"),
    "openai": ("openai", "AsyncOpenAI"),
}


def _import_mistral():
    """Mistral SDK: 1.x = `from mistralai import Mistral`; 2.x = `from mistralai.client`."""
    try:
        from mistralai import Mistral  # SDK 1.x

        return Mistral
    except (ImportError, AttributeError):
        from mistralai.client import Mistral  # SDK 2.x

        return Mistral


def _lib_check(provider: str) -> tuple[bool, str | None]:
    try:
        if provider == "mistral":
            _import_mistral()
        else:
            mod, cls = _IMPORT_CHECK[provider]
            m = __import__(mod, fromlist=[cls])
            getattr(m, cls)
        return True, None
    except Exception as e:  # noqa: BLE001 — import rusak/tak lengkap juga dianggap not-ok
        mod = _IMPORT_CHECK[provider][0]
        return False, f"library '{mod}' error: {type(e).__name__}: {e}"


def provider_status() -> dict[str, dict]:
    """Status tiap provider: has_key, lib_ok (import nyata), configured, reason."""
    out: dict[str, dict] = {}
    for p in ("claude", "mistral", "openai"):
        has_key = bool(getattr(settings, _KEY_ATTR[p], None))
        lib_ok, lib_err = _lib_check(p)
        reasons = []
        if not has_key:
            reasons.append(f"{_KEY_ATTR[p].upper()} belum diisi")
        if lib_err:
            reasons.append(lib_err)
        out[p] = {
            "provider": p,
            "has_key": has_key,
            "lib_ok": lib_ok,
            "configured": has_key and lib_ok,
            "default_model": settings.default_ai_model_parser if p == "claude"
            else ("mistral-large-latest" if p == "mistral" else "gpt-4o-mini"),
            "reason": "; ".join(reasons) or "siap",
        }
    return out


def _configured(provider: str) -> bool:
    s = provider_status().get(provider, {})
    return bool(s.get("configured"))


def any_provider_configured() -> bool:
    return any(s["configured"] for s in provider_status().values())



@dataclass
class AIMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class AIResponse:
    text: str
    provider: ProviderName
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None


class AIClient:
    """Unified client with provider fallback."""

    def __init__(self):
        self._anthropic = None
        self._mistral = None
        self._openai = None
        # Provider yang gagal permanen (auth/akun) → di-skip sisa proses agar tak
        # menghajar API tiap item (mis. matcher 1351 item). Direset saat restart.
        self._disabled: dict[str, str] = {}

    def _get_anthropic(self):
        if self._anthropic is None:
            if not settings.anthropic_api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not set")
            from anthropic import AsyncAnthropic

            self._anthropic = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._anthropic

    def _get_mistral(self):
        if self._mistral is None:
            if not settings.mistral_api_key:
                raise RuntimeError("MISTRAL_API_KEY not set")
            mistral_cls = _import_mistral()
            self._mistral = mistral_cls(api_key=settings.mistral_api_key)
        return self._mistral

    def _get_openai(self):
        if self._openai is None:
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            from openai import AsyncOpenAI

            self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception(_is_retryable))
    async def _call_claude(
        self,
        messages: list[AIMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        client = self._get_anthropic()
        # Separate system from messages
        system = "\n\n".join(m.content for m in messages if m.role == "system") or None
        msgs = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": msgs,
        }
        if system:
            kwargs["system"] = system
        resp = await client.messages.create(**kwargs)
        text = "".join(
            block.text for block in resp.content if hasattr(block, "text")
        )
        return AIResponse(
            text=text,
            provider="claude",
            model=model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            raw=resp,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception(_is_retryable))
    async def _call_mistral(
        self,
        messages: list[AIMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        client = self._get_mistral()
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        resp = await client.chat.complete_async(
            model=model,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = resp.choices[0].message.content if resp.choices else ""
        return AIResponse(
            text=text,
            provider="mistral",
            model=model,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            raw=resp,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception(_is_retryable))
    async def _call_openai(
        self,
        messages: list[AIMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> AIResponse:
        client = self._get_openai()
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        resp = await client.chat.completions.create(
            model=model,
            messages=msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = resp.choices[0].message.content or ""
        return AIResponse(
            text=text,
            provider="openai",
            model=model,
            input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            raw=resp,
        )

    async def complete(
        self,
        messages: list[AIMessage],
        model: str | None = None,
        provider: ProviderName | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        fallback: bool = True,
    ) -> AIResponse:
        """Complete a prompt. Uses default provider, with fallback chain."""
        provider = provider or settings.default_ai_provider
        model = model or self._default_model(provider)

        # Build attempt list
        attempts: list[ProviderName] = [provider]
        if fallback:
            for p in settings.ai_fallback_order:
                if p != provider and p not in attempts:
                    attempts.append(p)

        # Fail-fast: hanya provider yang TERKONFIGURASI (ada key + lib) dan belum
        # di-disable (gagal auth permanen). Mencegah retry storm.
        attempts = [p for p in attempts if _configured(p) and p not in self._disabled]
        if not attempts:
            disabled = "; ".join(f"{k}: {v}" for k, v in self._disabled.items())
            raise RuntimeError(
                "Tidak ada AI provider yang bisa dipakai. "
                + (f"Provider dimatikan ({disabled}). " if disabled else "")
                + "Set/perbaiki ANTHROPIC_API_KEY / MISTRAL_API_KEY / OPENAI_API_KEY di server."
            )

        last_error: Exception | None = None
        for prov in attempts:
            try:
                method = {
                    "claude": self._call_claude,
                    "mistral": self._call_mistral,
                    "openai": self._call_openai,
                }[prov]
                prov_model = model if prov == provider else self._default_model(prov)
                return await method(messages, prov_model, max_tokens, temperature)
            except Exception as e:
                detail = _explain(e)
                last_error = e
                sc = _http_status(_root_cause(e))
                # Error auth/akun (401/403) → matikan provider untuk sisa proses.
                if sc in (401, 403):
                    self._disabled[prov] = detail
                    logger.error(
                        f"AI provider {prov} DINONAKTIFKAN (gagal auth): {detail}. "
                        "Periksa API key/akun di server."
                    )
                else:
                    logger.warning(f"AI provider {prov} failed: {detail}. Coba fallback berikutnya.")
                await asyncio.sleep(0.2)
                continue

        raise RuntimeError(f"All AI providers failed. Last error: {_explain(last_error) if last_error else 'n/a'}")

    def _default_model(self, provider: ProviderName) -> str:
        return {
            "claude": settings.default_ai_model_parser,
            "mistral": "mistral-large-latest",
            "openai": "gpt-4o-mini",
        }[provider]

    async def complete_json(
        self,
        messages: list[AIMessage],
        schema_hint: str = "",
        **kwargs,
    ) -> dict:
        """Complete and parse as JSON. Adds JSON instruction to last user message."""
        if messages and messages[-1].role == "user" and schema_hint:
            messages = list(messages)
            messages[-1] = AIMessage(
                role="user",
                content=(
                    messages[-1].content
                    + f"\n\nResponse format (JSON only, no markdown):\n{schema_hint}"
                ),
            )
        resp = await self.complete(messages, **kwargs)
        text = resp.text.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            lines = [ln for ln in text.split("\n") if not ln.startswith("```")]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI: {text[:500]}")
            raise ValueError(f"Invalid JSON from AI: {e}") from e


# Singleton instance
ai_client = AIClient()
