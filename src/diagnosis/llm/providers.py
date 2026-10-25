"""Concrete LLM provider adapters for OpenAI, Google Gemini, Anthropic, and local Mock engines.

All network calls use standard HTTP requests with explicit timeouts and credential masking.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional
import requests

from config.settings import Settings, get_settings
from src.diagnosis.llm.base import (
    BaseLLMProvider,
    LLMAuthenticationError,
    LLMError,
    LLMRateLimitError,
    LLMResponse,
    LLMResponseFormatError,
    LLMTimeoutError,
    mask_credential,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAICompatibleProvider(BaseLLMProvider):
    """Adapter for OpenAI, Azure OpenAI, Ollama, Groq, vLLM, or any OpenAI-compatible endpoint."""

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(model_name=model_name, api_key=api_key, timeout_seconds=timeout_seconds)
        self.base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMAuthenticationError(
                "OpenAI API key missing. Configure OPENAI_API_KEY or LLM_API_KEY in environment."
            )

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

        url = f"{self.base_url}/chat/completions"
        start_time = time.time()
        logger.info(
            "Dispatching LLM request to %s (model: %s, key: %s)",
            self.provider_name,
            self.model_name,
            mask_credential(self.api_key),
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"OpenAI API request timed out after {self.timeout_seconds}s: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(f"Network connection failed to {self.base_url}: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected HTTP request error: {exc}") from exc

        elapsed = time.time() - start_time

        if resp.status_code in (401, 403):
            raise LLMAuthenticationError(f"Authentication failed (HTTP {resp.status_code}): {resp.text}")
        elif resp.status_code == 429:
            raise LLMRateLimitError(f"Rate limit or quota exceeded (HTTP 429): {resp.text}")
        elif resp.status_code != 200:
            raise LLMError(f"Provider returned error HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                execution_time_s=round(elapsed, 3),
                raw_response=data,
            )
        except (KeyError, IndexError) as exc:
            raise LLMResponseFormatError(f"Unexpected response format from OpenAI API: {exc}") from exc


class GeminiProvider(BaseLLMProvider):
    """Adapter for Google Gemini models via Google AI Studio API."""

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(model_name=model_name, api_key=api_key, timeout_seconds=timeout_seconds)

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Gemini API key missing. Configure GEMINI_API_KEY or LLM_API_KEY in environment."
            )

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )
        headers = {"Content-Type": "application/json"}

        parts = []
        if system_prompt:
            parts.append({"text": f"SYSTEM INSTRUCTION: {system_prompt}\n\n"})
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }

        start_time = time.time()
        logger.info(
            "Dispatching LLM request to %s (model: %s, key: %s)",
            self.provider_name,
            self.model_name,
            mask_credential(self.api_key),
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"Gemini API request timed out after {self.timeout_seconds}s: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(f"Network connection failed to Gemini API: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected HTTP error connecting to Gemini API: {exc}") from exc

        elapsed = time.time() - start_time

        if resp.status_code in (401, 403):
            raise LLMAuthenticationError(f"Gemini authentication failed (HTTP {resp.status_code}): {resp.text}")
        elif resp.status_code == 429:
            raise LLMRateLimitError(f"Gemini rate limit or quota exceeded (HTTP 429): {resp.text}")
        elif resp.status_code != 200:
            raise LLMError(f"Gemini API returned error HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            candidate = data["candidates"][0]
            content = candidate["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            return LLMResponse(
                content=content,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
                execution_time_s=round(elapsed, 3),
                raw_response=data,
            )
        except (KeyError, IndexError) as exc:
            raise LLMResponseFormatError(f"Malformed Gemini response payload: {exc}") from exc


class AnthropicProvider(BaseLLMProvider):
    """Adapter for Anthropic Claude models via Messages API."""

    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        super().__init__(model_name=model_name, api_key=api_key, timeout_seconds=timeout_seconds)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        if not self.api_key:
            raise LLMAuthenticationError(
                "Anthropic API key missing. Configure ANTHROPIC_API_KEY or LLM_API_KEY in environment."
            )

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            payload["system"] = system_prompt

        start_time = time.time()
        logger.info(
            "Dispatching LLM request to %s (model: %s, key: %s)",
            self.provider_name,
            self.model_name,
            mask_credential(self.api_key),
        )

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_seconds)
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(f"Anthropic API request timed out after {self.timeout_seconds}s: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMError(f"Network connection failed to Anthropic API: {exc}") from exc
        except Exception as exc:
            raise LLMError(f"Unexpected HTTP error connecting to Anthropic API: {exc}") from exc

        elapsed = time.time() - start_time

        if resp.status_code in (401, 403):
            raise LLMAuthenticationError(f"Anthropic authentication failed (HTTP {resp.status_code}): {resp.text}")
        elif resp.status_code == 429:
            raise LLMRateLimitError(f"Anthropic rate limit exceeded (HTTP 429): {resp.text}")
        elif resp.status_code != 200:
            raise LLMError(f"Anthropic API returned error HTTP {resp.status_code}: {resp.text}")

        data = resp.json()
        try:
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            return LLMResponse(
                content=content,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                execution_time_s=round(elapsed, 3),
                raw_response=data,
            )
        except (KeyError, IndexError) as exc:
            raise LLMResponseFormatError(f"Malformed Anthropic response payload: {exc}") from exc


class MockLLMProvider(BaseLLMProvider):
    """Deterministic in-memory mock provider for testing and offline execution without credentials."""

    def __init__(
        self,
        model_name: str = "mock-model-v1",
        api_key: Optional[str] = "mock_key_test",
        fixed_response: Optional[str] = None,
        simulate_error: Optional[str] = None,  # 'timeout', 'rate_limit', 'auth', 'malformed'
    ):
        super().__init__(model_name=model_name, api_key=api_key)
        self.fixed_response = fixed_response
        self.simulate_error = simulate_error
        self.call_count = 0
        self.last_prompt: Optional[str] = None
        self.last_system_prompt: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt

        if self.simulate_error == "timeout":
            raise LLMTimeoutError("Simulated LLM API request timeout.")
        elif self.simulate_error == "rate_limit":
            raise LLMRateLimitError("Simulated HTTP 429 rate limit reached.")
        elif self.simulate_error == "auth":
            raise LLMAuthenticationError("Simulated invalid or rejected credentials.")
        elif self.simulate_error == "malformed":
            return LLMResponse(
                content="<<<This is not valid JSON content>>>",
                model=self.model_name,
                provider=self.provider_name,
                execution_time_s=0.01,
            )

        if self.fixed_response:
            return LLMResponse(
                content=self.fixed_response,
                model=self.model_name,
                provider=self.provider_name,
                prompt_tokens=150,
                completion_tokens=200,
                total_tokens=350,
                execution_time_s=0.02,
            )

        # 1. Parse target subsystem and fault code from prompt
        sub_match = re.search(r'Target Subsystem\s*:\s*([^\n\r]+)', prompt)
        target_subsystem = sub_match.group(1).strip() if sub_match else "door_system"

        code_match = re.search(r'OEM Fault Code\s*:\s*([^\n\r]+)', prompt)
        target_code = code_match.group(1).strip() if code_match else "None"
        if "None" in target_code:
            target_code = ""

        # 2. Extract allowed citation IDs
        cited_cases: List[str] = []
        match = re.search(r'\[ALLOWED CITATION CASE IDS\]\s*\[(.*?)\]', prompt)
        if match and match.group(1).strip() and match.group(1).strip() != "None":
            extracted = [x.strip().strip('"').strip("'") for x in match.group(1).split(",") if x.strip()]
            cited_cases = extracted

        # 3. Extract retrieved case blocks from prompt
        case_pattern = re.compile(
            r'--- BEGIN RETRIEVED CASE: \[(?P<case_id>[^\]]+)\] ---\s*'
            r'Subsystem:\s*(?P<subsystem>[^\n\r]+)\s*'
            r'Diagnostic Fault Code:\s*(?P<fault_code>[^\n\r]+)\s*.*?'
            r'Confirmed Root Cause:\s*(?P<root_cause>[^\n\r]+)\s*'
            r'Documented Corrective Action:\s*(?P<action>[^\n\r]+)',
            re.DOTALL
        )
        parsed_cases = [m.groupdict() for m in case_pattern.finditer(prompt)]

        # 4. Formulate candidate causes based on parsed cases or novel fault
        candidate_causes = []
        if parsed_cases:
            for idx, c in enumerate(parsed_cases[:2], start=1):
                cid = c["case_id"].strip()
                valid_cites = [cid] if cid in cited_cases else (cited_cases[:1] if cited_cases else [])
                band = "likely" if idx == 1 else "possible"
                candidate_causes.append({
                    "rank": idx,
                    "hypothesis_title": c["root_cause"].strip(),
                    "subsystem": c["subsystem"].strip(),
                    "probability_band": band,
                    "explanation": (
                        f"Technician report aligns with historical precedent [{cid}] "
                        f"for subsystem '{c['subsystem'].strip()}'. "
                        f"Precedent documents confirmed root cause: '{c['root_cause'].strip()}'."
                    ),
                    "supporting_case_ids": valid_cites,
                    "conflicting_evidence": [],
                    "recommended_checks": [
                        f"Perform targeted multimeter continuity and physical inspection of {c['subsystem'].strip()}",
                        f"Verify operating tolerances against OEM technical manual for fault code {c['fault_code'].strip() or target_code or 'general'}",
                    ],
                    "documented_corrective_actions": [
                        c["action"].strip(),
                    ],
                })
            summary = (
                f"Diagnostic synthesis for subsystem '{target_subsystem}': Identified "
                f"{len(candidate_causes)} candidate cause(s) grounded in historical precedents. "
                f"Primary root cause hypothesis: '{candidate_causes[0]['hypothesis_title']}'."
            )
            score = 0.78
        else:
            candidate_causes.append({
                "rank": 1,
                "hypothesis_title": f"Unindexed or novel anomalous condition in {target_subsystem}",
                "subsystem": target_subsystem,
                "probability_band": "unlikely",
                "explanation": (
                    f"No matching historical precedents retrieved from knowledge base for subsystem '{target_subsystem}'. "
                    "Physical instrumentation testing and manual controller log analysis required."
                ),
                "supporting_case_ids": [],
                "conflicting_evidence": [],
                "recommended_checks": [
                    f"Perform baseline multimeter voltage checks on {target_subsystem} power rails",
                    "Extract controller diagnostic event buffer via hand-held service tool",
                ],
                "documented_corrective_actions": [
                    f"Perform physical visual inspection of {target_subsystem} assembly",
                ],
            })
            summary = (
                f"Insufficient historical evidence matching '{target_subsystem}'. "
                "Baseline physical troubleshooting protocol required."
            )
            score = 0.15

        default_json = {
            "summary": summary,
            "candidate_causes": candidate_causes,
            "uncertainty_and_missing_info": [
                f"Field controller diagnostic buffer register for '{target_subsystem}' not attached in telemetry"
            ],
            "safety_advisories": [
                f"Place elevator car on INDEPENDENT SERVICE mode before entering {target_subsystem} workspace"
            ],
            "confidence_score": score,
        }

        return LLMResponse(
            content=json.dumps(default_json, indent=2),
            model=self.model_name,
            provider=self.provider_name,
            prompt_tokens=220,
            completion_tokens=260,
            total_tokens=480,
            execution_time_s=0.03,
        )


def get_llm_provider(
    settings: Optional[Settings] = None,
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """Factory creating appropriate LLM provider adapter based on configuration."""
    cfg = settings or get_settings()
    p_name = (provider_name or cfg.llm_provider).strip().lower()
    key = api_key or cfg.llm_api_key
    m_name = model_name or cfg.llm_model

    # Check for demo mode / offline
    if cfg.is_demo_mode or p_name in ("mock", "offline", "none", ""):
        return MockLLMProvider(model_name=m_name or "mock-offline", api_key=key)

    if p_name in ("openai", "azure_openai", "groq", "ollama", "vllm"):
        return OpenAICompatibleProvider(model_name=m_name or "gpt-4o-mini", api_key=key)
    elif p_name in ("gemini", "google"):
        return GeminiProvider(model_name=m_name or "gemini-1.5-flash", api_key=key)
    elif p_name in ("anthropic", "claude"):
        return AnthropicProvider(model_name=m_name or "claude-3-5-sonnet-20241022", api_key=key)
    else:
        logger.warning("Unrecognized LLM provider '%s'; defaulting to OpenAICompatibleProvider.", p_name)
        return OpenAICompatibleProvider(model_name=m_name or "gpt-4o-mini", api_key=key)
