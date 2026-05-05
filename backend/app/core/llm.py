"""
Modular LLM Interface
=====================
Supports:  OpenAI GPT-4o  |  Any OpenAI-compatible local endpoint (Ollama, LM Studio, etc.)

Usage:
    llm = get_llm_client()
    response = await llm.complete(messages=[...], temperature=0.2)
    stream   = llm.stream(messages=[...])
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any

import httpx
from openai import AsyncOpenAI

from app.core.config import settings


# ─────────────────────────────────────────────────────────────
# Base interface
# ─────────────────────────────────────────────────────────────

class BaseLLM(ABC):
    """Abstract base that every LLM adapter must implement."""

    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        """Return a complete text response."""

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Yield text chunks as they arrive."""


# ─────────────────────────────────────────────────────────────
# OpenAI adapter
# ─────────────────────────────────────────────────────────────

class OpenAILLM(BaseLLM):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async with await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        ) as resp:
            async for chunk in resp:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta


# ─────────────────────────────────────────────────────────────
# Local / Ollama adapter  (OpenAI-compatible REST)
# ─────────────────────────────────────────────────────────────

class LocalLLM(BaseLLM):
    def __init__(self):
        self._base_url = settings.LOCAL_LLM_BASE_URL.rstrip("/")
        self._model = settings.LOCAL_LLM_MODEL
        self._client = httpx.AsyncClient(timeout=120.0)

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        resp = await self._client.post(
            f"{self._base_url}/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    async def stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        async with self._client.stream(
            "POST",
            f"{self._base_url}/chat/completions",
            json=payload,
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                try:
                    chunk = json.loads(raw)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError):
                    continue


# ─────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────

_llm_instance: BaseLLM | None = None


def get_llm_client() -> BaseLLM:
    global _llm_instance
    if _llm_instance is None:
        if settings.LLM_PROVIDER == "openai":
            _llm_instance = OpenAILLM()
        else:
            _llm_instance = LocalLLM()
    return _llm_instance
