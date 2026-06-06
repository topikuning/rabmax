"""Multi-provider AI client abstraction.

Supports Claude (Anthropic), Mistral, and OpenAI with automatic fallback.
All providers return same response shape via internal normalization.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Literal

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

ProviderName = Literal["claude", "mistral", "openai"]


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
            from mistralai import Mistral

            self._mistral = Mistral(api_key=settings.mistral_api_key)
        return self._mistral

    def _get_openai(self):
        if self._openai is None:
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY not set")
            from openai import AsyncOpenAI

            self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        return self._openai

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
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
                logger.warning(
                    f"AI provider {prov} failed: {e}. Trying next in fallback chain."
                )
                last_error = e
                await asyncio.sleep(0.5)
                continue

        raise RuntimeError(f"All AI providers failed. Last error: {last_error}")

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
            lines = text.split("\n")
            lines = [
                l
                for l in lines
                if not l.startswith("```")
            ]
            text = "\n".join(lines).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from AI: {text[:500]}")
            raise ValueError(f"Invalid JSON from AI: {e}") from e


# Singleton instance
ai_client = AIClient()
