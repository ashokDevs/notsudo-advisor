from __future__ import annotations

import json
import os
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from core.config import llm_api_key, llm_base_url, llm_models
from core.observability.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """
    Two-tier LLM wrapper via OpenAI-compatible API.

    Works with:
      - OpenAI (OPENAI_API_KEY)
      - OpenRouter (sk-or-... + OPENAI_API_BASE=https://openrouter.ai/api/v1)
      - Groq / Azure / local gateways (set OPENAI_API_BASE)

    Falls back to None when no key is configured (caller uses heuristics).
    """

    def __init__(
        self,
        api_key: str | None = None,
        cheap_model: str | None = None,
        frontier_model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        cheap_default, frontier_default = llm_models()
        self.api_key = api_key if api_key is not None else llm_api_key()
        self.cheap_model = cheap_model or cheap_default
        self.frontier_model = frontier_model or frontier_default
        self.base_url = base_url if base_url is not None else llm_base_url()
        self._clients: dict[str, Any] = {}

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _model_for_tier(self, tier: str) -> str:
        if tier == "cheap":
            return self.cheap_model
        if tier == "frontier":
            return self.frontier_model
        raise ValueError(f"Unknown tier {tier!r}; pass 'cheap' or 'frontier'")

    def _get_chat(self, tier: str) -> Any:
        model = self._model_for_tier(tier)
        cache_key = f"{self.base_url or 'default'}::{model}"
        if cache_key not in self._clients:
            from langchain_openai import ChatOpenAI

            kwargs: dict[str, Any] = {
                "model": model,
                "api_key": self.api_key,
                "temperature": 0,
                "timeout": 90,
                "max_retries": 2,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url

            # OpenRouter recommends these headers
            default_headers: dict[str, str] = {}
            if self.base_url and "openrouter.ai" in self.base_url:
                default_headers["HTTP-Referer"] = os.getenv(
                    "APP_BASE_URL", "http://localhost:8080"
                )
                default_headers["X-Title"] = "NotSudo Advisor"
            if default_headers:
                kwargs["default_headers"] = default_headers

            logger.info(
                "llm client ready",
                model=model,
                base_url=self.base_url or "https://api.openai.com/v1",
                tier=tier,
            )
            self._clients[cache_key] = ChatOpenAI(**kwargs)
        return self._clients[cache_key]

    async def complete(
        self,
        *,
        tier: str,
        system: str,
        user: str,
        response_format: type[T] | None = None,
    ) -> T | str | None:
        if not self.available:
            logger.warning("LLM unavailable — no OPENAI_API_KEY / LLM_API_KEY")
            return None

        try:
            chat = self._get_chat(tier)
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=system),
                HumanMessage(content=user),
            ]
            if response_format is not None:
                try:
                    structured = chat.with_structured_output(response_format)
                    result = await structured.ainvoke(messages)
                    if isinstance(result, response_format):
                        return result
                    if isinstance(result, dict):
                        return response_format.model_validate(result)
                except Exception as exc:
                    logger.warning(
                        "structured output failed, falling back to JSON parse",
                        error=str(exc),
                    )

            response = await chat.ainvoke(messages)
            content = str(response.content)
            if response_format is None:
                return content
            parsed = self._extract_json(content)
            if parsed is None:
                return None
            return response_format.model_validate(parsed)
        except Exception as exc:
            logger.error("LLM call failed", tier=tier, error=str(exc))
            return None

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any] | None:
        content = content.strip()
        try:
            data = json.loads(content)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


_default: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _default
    if _default is None:
        _default = LLMClient()
    return _default


def reset_llm_client() -> None:
    """Call after reloading .env so a new key/base_url is picked up."""
    global _default
    _default = None
