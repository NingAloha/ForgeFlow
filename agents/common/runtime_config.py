from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LLMRuntimeConfig:
    enabled: bool = False
    provider: str = "deepseek"
    protocol: str = "openai"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    api_key: str = ""
    api_key_env: str = "DEEPSEEK_API_KEY"
    timeout: float = 20.0
    temperature: float = 0.2
    max_tokens: int = 800
    fallback_on_error: bool = True
    execution_mode: str = "strict_llm"
    enabled_stages: list[str] = None  # type: ignore[assignment]
    retry_policy_by_stage: dict[str, int] = None  # type: ignore[assignment]
    max_repair_attempts: int = 1
    strict_unknown_fields: bool = True

    def __post_init__(self) -> None:
        if self.enabled_stages is None:
            self.enabled_stages = [
                "REQUIREMENTS",
                "SOLUTION",
                "DESIGN",
                "IMPLEMENTATION",
                "TESTING",
            ]
        if self.retry_policy_by_stage is None:
            self.retry_policy_by_stage = {
                "REQUIREMENTS": 2,
                "SOLUTION": 2,
                "DESIGN": 2,
                "IMPLEMENTATION": 2,
                "TESTING": 1,
            }


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_llm_runtime_config(
    config_path: str | Path = "llm_config.local.json",
) -> LLMRuntimeConfig:
    config = LLMRuntimeConfig()
    default_config_path = str(config_path) == "llm_config.local.json"
    argv_joined = " ".join(sys.argv).lower()
    is_test_process = bool(os.getenv("PYTEST_CURRENT_TEST")) or (
        " -m unittest" in f" {argv_joined}"
        or " -m pytest" in f" {argv_joined}"
        or "pytest" in (sys.argv[0].lower() if sys.argv else "")
    )
    if (
        default_config_path
        and is_test_process
        and not _as_bool(os.getenv("FORGEFLOW_LLM_ALLOW_IN_TESTS"), False)
    ):
        return config
    path = Path(config_path)
    payload: dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                payload = loaded
        except json.JSONDecodeError:
            payload = {}

    config.enabled = _as_bool(payload.get("enabled"), config.enabled)
    config.provider = str(payload.get("provider", config.provider))
    config.protocol = str(payload.get("protocol", config.protocol))
    config.base_url = str(payload.get("base_url", config.base_url))
    config.model = str(payload.get("model", config.model))
    config.api_key = str(payload.get("api_key", config.api_key)).strip()
    config.api_key_env = str(payload.get("api_key_env", config.api_key_env))
    config.timeout = float(payload.get("timeout", config.timeout))
    config.temperature = float(payload.get("temperature", config.temperature))
    config.max_tokens = int(payload.get("max_tokens", config.max_tokens))
    config.fallback_on_error = _as_bool(
        payload.get("fallback_on_error"), config.fallback_on_error
    )
    config.execution_mode = (
        str(payload.get("execution_mode", config.execution_mode)).strip()
        or config.execution_mode
    )
    payload_enabled_stages = payload.get("enabled_stages")
    if isinstance(payload_enabled_stages, list):
        config.enabled_stages = [
            str(item).strip().upper()
            for item in payload_enabled_stages
            if str(item).strip()
        ] or config.enabled_stages
    payload_retry_policy = payload.get("retry_policy_by_stage")
    if isinstance(payload_retry_policy, dict):
        retry_policy: dict[str, int] = {}
        for stage, attempts in payload_retry_policy.items():
            key = str(stage).strip().upper()
            if not key:
                continue
            retry_policy[key] = max(0, _as_int(attempts, 0))
        if retry_policy:
            config.retry_policy_by_stage = retry_policy
    config.max_repair_attempts = max(
        0,
        _as_int(payload.get("max_repair_attempts"), config.max_repair_attempts),
    )
    config.strict_unknown_fields = _as_bool(
        payload.get("strict_unknown_fields"),
        config.strict_unknown_fields,
    )

    # Environment variable overrides for quick testing.
    config.enabled = _as_bool(os.getenv("FORGEFLOW_LLM_ENABLED"), config.enabled)
    config.provider = os.getenv("FORGEFLOW_LLM_PROVIDER", config.provider)
    config.protocol = os.getenv("FORGEFLOW_LLM_PROTOCOL", config.protocol)
    config.base_url = os.getenv("FORGEFLOW_LLM_BASE_URL", config.base_url)
    config.model = os.getenv("FORGEFLOW_LLM_MODEL", config.model)
    config.api_key = os.getenv("FORGEFLOW_LLM_API_KEY", config.api_key).strip()
    config.api_key_env = os.getenv("FORGEFLOW_LLM_API_KEY_ENV", config.api_key_env)
    config.timeout = float(os.getenv("FORGEFLOW_LLM_TIMEOUT", str(config.timeout)))
    config.temperature = float(
        os.getenv("FORGEFLOW_LLM_TEMPERATURE", str(config.temperature))
    )
    config.max_tokens = int(
        os.getenv("FORGEFLOW_LLM_MAX_TOKENS", str(config.max_tokens))
    )
    config.execution_mode = os.getenv(
        "FORGEFLOW_LLM_EXECUTION_MODE", config.execution_mode
    )
    raw_enabled_stages = os.getenv("FORGEFLOW_LLM_ENABLED_STAGES", "")
    if raw_enabled_stages.strip():
        config.enabled_stages = [
            item.strip().upper()
            for item in raw_enabled_stages.split(",")
            if item.strip()
        ] or config.enabled_stages
    raw_retry_policy = os.getenv("FORGEFLOW_LLM_RETRY_POLICY_BY_STAGE", "")
    if raw_retry_policy.strip():
        try:
            parsed_retry = json.loads(raw_retry_policy)
        except json.JSONDecodeError:
            parsed_retry = {}
        if isinstance(parsed_retry, dict):
            retry_policy: dict[str, int] = {}
            for stage, attempts in parsed_retry.items():
                key = str(stage).strip().upper()
                if not key:
                    continue
                retry_policy[key] = max(0, _as_int(attempts, 0))
            if retry_policy:
                config.retry_policy_by_stage = retry_policy
    config.max_repair_attempts = max(
        0,
        _as_int(
            os.getenv("FORGEFLOW_LLM_MAX_REPAIR_ATTEMPTS"),
            config.max_repair_attempts,
        ),
    )
    config.strict_unknown_fields = _as_bool(
        os.getenv("FORGEFLOW_LLM_STRICT_UNKNOWN_FIELDS"),
        config.strict_unknown_fields,
    )
    config.fallback_on_error = _as_bool(
        os.getenv("FORGEFLOW_LLM_FALLBACK_ON_ERROR"),
        config.fallback_on_error,
    )
    return config
