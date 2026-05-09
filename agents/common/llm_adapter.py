from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .runtime_config import LLMRuntimeConfig


@dataclass(slots=True)
class LLMCallResult:
    ok: bool
    content: dict[str, Any]
    error: str = ""
    model: str = ""
    latency_ms: int = 0


class LLMAdapter:
    def resolve_api_key(self, config: LLMRuntimeConfig) -> tuple[str, str]:
        if config.api_key:
            return config.api_key.strip(), "config"
        api_key = os.getenv(config.api_key_env, "").strip()
        if api_key:
            return api_key, "env"
        return "", ""

    def generate_requirements(
        self,
        user_input: str,
        config: LLMRuntimeConfig,
    ) -> LLMCallResult:
        api_key, _source = self.resolve_api_key(config)
        if not api_key:
            return LLMCallResult(
                ok=False,
                content={},
                error=(
                    "Missing API key. Set llm_config.local.json.api_key "
                    f"or env {config.api_key_env}."
                ),
                model=config.model,
                latency_ms=0,
            )

        start = time.time()
        payload = {
            "model": config.model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract requirement state as strict JSON. "
                        "Return only JSON with keys: project_goal, "
                        "functional_requirements, acceptance_criteria."
                    ),
                },
                {"role": "user", "content": user_input},
            ],
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url=f"{config.base_url.rstrip('/')}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=config.timeout) as response:
                raw = response.read().decode("utf-8")
            response_json = json.loads(raw)
            content_text = (
                response_json.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            content = json.loads(content_text) if content_text else {}
            latency_ms = int((time.time() - start) * 1000)
            if not isinstance(content, dict):
                return LLMCallResult(
                    ok=False,
                    content={},
                    error="LLM content is not a JSON object.",
                    model=config.model,
                    latency_ms=latency_ms,
                )
            return LLMCallResult(
                ok=True,
                content=content,
                model=config.model,
                latency_ms=latency_ms,
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            latency_ms = int((time.time() - start) * 1000)
            return LLMCallResult(
                ok=False,
                content={},
                error=str(exc),
                model=config.model,
                latency_ms=latency_ms,
            )
