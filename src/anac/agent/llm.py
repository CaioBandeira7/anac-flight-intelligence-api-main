"""Minimal client for any OpenAI-compatible chat API. Errors never carry the key or the raw body."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def load_env_file(path: Path) -> None:
    """Read KEY=value lines. Real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True, repr=False)
class LlmConfig:
    provider: str
    base_url: str
    model: str
    api_key: str | None
    timeout_seconds: float = 45.0

    @classmethod
    def from_env(cls) -> LlmConfig:
        return cls(
            provider=os.environ.get("ANAC_LLM_PROVIDER", "groq"),
            base_url=os.environ.get("ANAC_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            model=os.environ.get("ANAC_LLM_MODEL", DEFAULT_MODEL),
            api_key=os.environ.get("ANAC_LLM_API_KEY") or os.environ.get("GROQ_API_KEY") or None,
        )

    def __repr__(self) -> str:
        return f"LlmConfig(provider={self.provider!r}, model={self.model!r})"


class LlmErrorCode(StrEnum):
    NOT_CONFIGURED = "not_configured"
    AUTH = "auth_failed"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    BAD_OUTPUT = "bad_model_output"


class LlmError(Exception):
    def __init__(self, code: LlmErrorCode, retry_after: int | None = None) -> None:
        super().__init__(code.value)
        self.code = code
        self.retry_after = retry_after


class LlmClient:
    def __init__(self, config: LlmConfig, transport: httpx.BaseTransport | None = None) -> None:
        self.config = config
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        if not self.config.api_key:
            raise LlmError(LlmErrorCode.NOT_CONFIGURED)
        return {"Authorization": f"Bearer {self.config.api_key}"}

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> httpx.Response:
        try:
            with httpx.Client(
                transport=self._transport, timeout=self.config.timeout_seconds
            ) as client:
                return client.request(
                    method, f"{self.config.base_url}{path}", headers=self._headers(), json=payload
                )
        except httpx.TimeoutException:
            raise LlmError(LlmErrorCode.TIMEOUT) from None
        except httpx.HTTPError:
            raise LlmError(LlmErrorCode.UNAVAILABLE) from None

    def _raise_for_status(self, response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        if status in (401, 403):
            raise LlmError(LlmErrorCode.AUTH)
        if status == 429:
            header = response.headers.get("retry-after", "")
            raise LlmError(LlmErrorCode.RATE_LIMITED, int(header) if header.isdigit() else None)
        if status == 400:
            # Groq answers 400 when the model produced an invalid tool call.
            raise LlmError(LlmErrorCode.BAD_OUTPUT)
        raise LlmError(LlmErrorCode.UNAVAILABLE)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/chat/completions",
            {
                "model": self.config.model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "temperature": 0.1,
                "max_completion_tokens": 900,
            },
        )
        self._raise_for_status(response)
        try:
            message: dict[str, Any] = response.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError):
            raise LlmError(LlmErrorCode.BAD_OUTPUT) from None
        return message

    def model_available(self) -> bool:
        """Whether the configured model is listed for this account."""
        response = self._request("GET", "/models")
        self._raise_for_status(response)
        try:
            return self.config.model in {item["id"] for item in response.json()["data"]}
        except (ValueError, KeyError, TypeError):
            raise LlmError(LlmErrorCode.UNAVAILABLE) from None
