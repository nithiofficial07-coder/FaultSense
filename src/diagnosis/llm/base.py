"""Base interfaces, data transfer models, and exceptions for LLM provider adapters."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


def mask_credential(key: Optional[str]) -> str:
    """Safely masks sensitive API keys, preventing exposure in logs and UI."""
    if not key or not str(key).strip():
        return "[NOT CONFIGURED]"
    s = str(key).strip()
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}...{s[-4:]}"


class LLMError(Exception):
    """Base exception for LLM provider communication failures."""


class LLMAuthenticationError(LLMError):
    """Raised when API credentials are missing, rejected, or expired."""


class LLMTimeoutError(LLMError):
    """Raised when an external LLM API request exceeds the configured timeout."""


class LLMRateLimitError(LLMError):
    """Raised when provider rate limits or quotas are exceeded (HTTP 429)."""


class LLMResponseFormatError(LLMError):
    """Raised when provider output cannot be parsed into required JSON structure."""


@dataclass
class LLMResponse:
    """Standardized response payload returned by any LLM provider adapter."""
    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    execution_time_s: float = 0.0
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseLLMProvider(ABC):
    """Abstract provider adapter isolating model-specific HTTP protocols from diagnostic reasoning."""

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the canonical provider identifier (e.g. 'openai', 'gemini', 'mock')."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        """Executes prompt completion and returns standardized LLMResponse."""
