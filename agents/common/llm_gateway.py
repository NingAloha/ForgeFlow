from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from schemas.llm_trace import LLMTraceModel

from .llm_adapter import LLMAdapter
from .runtime_config import LLMRuntimeConfig

RETRYABLE_FAILURES = {
    "timeout",
    "network_error",
    "rate_limit",
    "invalid_json",
    "schema_error",
    "empty_output",
}
FINAL_ERROR_STATUSES = {"retryable_error", "fatal_error", "needs_user_input"}


@dataclass(slots=True)
class PromptContract:
    stage_name: str
    system_prompt: str
    required_fields: list[str] = field(default_factory=list)
    reject_unknown_fields: bool = True
    allowed_fields: list[str] | None = None
    output_model: type[BaseModel] | None = None


@dataclass(slots=True)
class LLMStructuredResult:
    status: str
    parsed_output: dict[str, Any] | None
    validation_errors: list[str]
    raw_output: str
    repair_attempts: int
    confidence: float | None
    failure_type: str
    model: str
    provider: str
    protocol: str
    latency_ms: int
    error: str = ""

    def to_trace(self) -> LLMTraceModel:
        excerpt = self.raw_output.strip()
        if len(excerpt) > 800:
            excerpt = excerpt[:800]
        return LLMTraceModel(
            status=self.status,
            failure_type=self.failure_type,
            repair_attempts=self.repair_attempts,
            validation_errors=list(self.validation_errors),
            raw_excerpt=excerpt,
            model=self.model,
            provider=self.provider,
            protocol=self.protocol,
            latency_ms=self.latency_ms,
            error=self.error or None,
        )


class LLMGateway:
    def __init__(self, adapter: LLMAdapter | None = None) -> None:
        self.adapter = adapter or LLMAdapter()

    def generate(
        self,
        contract: PromptContract,
        user_prompt: str,
        config: LLMRuntimeConfig,
    ) -> LLMStructuredResult:
        max_attempts = 1 + max(0, self._retry_count(config, contract.stage_name))
        last_result = self._retryable_result(
            failure_type="unknown",
            raw_output="",
            error="LLM call did not run.",
            repair_attempts=0,
        )
        last_result.model = config.model
        last_result.provider = config.provider
        last_result.protocol = config.protocol

        for _ in range(max_attempts):
            transport = self.adapter.generate_text(
                system_prompt=contract.system_prompt,
                user_prompt=user_prompt,
                config=config,
            )
            if not transport.ok:
                failure_type = self._classify_transport_error(transport.error)
                status = (
                    "needs_user_input"
                    if failure_type == "policy_block"
                    else "retryable_error"
                    if failure_type in RETRYABLE_FAILURES
                    else "fatal_error"
                )
                last_result = LLMStructuredResult(
                    status=status,
                    parsed_output=None,
                    validation_errors=[],
                    raw_output=transport.raw_output,
                    repair_attempts=0,
                    confidence=None,
                    failure_type=failure_type,
                    model=config.model,
                    provider=config.provider,
                    protocol=config.protocol,
                    latency_ms=transport.latency_ms,
                    error=transport.error,
                )
                if status == "retryable_error":
                    continue
                return last_result

            parsed = self._parse_and_validate(
                raw_output=transport.raw_output,
                contract=contract,
                strict_unknown=config.strict_unknown_fields,
                max_repair_attempts=config.max_repair_attempts,
            )
            parsed.model = config.model
            parsed.provider = config.provider
            parsed.protocol = config.protocol
            parsed.latency_ms = transport.latency_ms

            if parsed.status == "retryable_error":
                last_result = parsed
                continue
            return parsed
        return last_result

    def _retry_count(self, config: LLMRuntimeConfig, stage_name: str) -> int:
        stage_key = str(stage_name).upper()
        return int(config.retry_policy_by_stage.get(stage_key, 0))

    def _parse_and_validate(
        self,
        raw_output: str,
        contract: PromptContract,
        strict_unknown: bool,
        max_repair_attempts: int,
    ) -> LLMStructuredResult:
        text = raw_output.strip()
        if not text:
            return self._retryable_result(
                failure_type="empty_output",
                raw_output=raw_output,
                error="Empty LLM output.",
                repair_attempts=0,
            )

        candidate = self._extract_json_text(text)
        repair_attempts = 0
        parsed_obj: Any = None
        decode_error = ""
        while True:
            try:
                parsed_obj = json.loads(candidate)
                break
            except json.JSONDecodeError as exc:
                decode_error = str(exc)
                if repair_attempts >= max(0, max_repair_attempts):
                    return self._retryable_result(
                        failure_type="invalid_json",
                        raw_output=raw_output,
                        error=decode_error,
                        repair_attempts=repair_attempts,
                    )
                repaired = self._repair_json(candidate)
                if repaired == candidate:
                    return self._retryable_result(
                        failure_type="invalid_json",
                        raw_output=raw_output,
                        error=decode_error,
                        repair_attempts=repair_attempts,
                    )
                candidate = repaired
                repair_attempts += 1

        if not isinstance(parsed_obj, dict):
            return self._retryable_result(
                failure_type="schema_error",
                raw_output=raw_output,
                error="LLM output JSON root must be an object.",
                repair_attempts=repair_attempts,
                validation_errors=["root must be object"],
            )

        validation_errors: list[str] = []
        if (
            strict_unknown
            and contract.reject_unknown_fields
            and contract.output_model is None
        ):
            allowed = set(contract.allowed_fields or [])
            if allowed:
                extras = sorted([key for key in parsed_obj if key not in allowed])
                if extras:
                    validation_errors.append(f"Unknown fields: {', '.join(extras)}")

        missing = [key for key in contract.required_fields if key not in parsed_obj]
        if missing:
            validation_errors.append(f"Missing required fields: {', '.join(missing)}")

        normalized: dict[str, Any] = dict(parsed_obj)
        if contract.output_model is not None:
            try:
                normalized = contract.output_model.model_validate(
                    parsed_obj
                ).model_dump(mode="python")
            except ValidationError as exc:
                validation_errors.extend(self._format_validation_errors(exc))

        if validation_errors:
            return self._retryable_result(
                failure_type="schema_error",
                raw_output=raw_output,
                error="Schema validation failed.",
                repair_attempts=repair_attempts,
                validation_errors=validation_errors,
            )

        return LLMStructuredResult(
            status="success",
            parsed_output=normalized,
            validation_errors=[],
            raw_output=raw_output,
            repair_attempts=repair_attempts,
            confidence=None,
            failure_type="none",
            model="",
            provider="",
            protocol="",
            latency_ms=0,
            error="",
        )

    def _extract_json_text(self, text: str) -> str:
        fenced = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE
        )
        if fenced:
            return fenced.group(1).strip()
        return text

    def _repair_json(self, text: str) -> str:
        fixed = text.strip()
        fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
        if fixed.count("{") > fixed.count("}"):
            fixed = fixed + ("}" * (fixed.count("{") - fixed.count("}")))
        if fixed.count("[") > fixed.count("]"):
            fixed = fixed + ("]" * (fixed.count("[") - fixed.count("]")))
        return fixed

    def _classify_transport_error(self, error: str) -> str:
        lowered = error.lower()
        if "timed out" in lowered or "timeout" in lowered:
            return "timeout"
        if (
            "401" in lowered
            or "403" in lowered
            or "unauthorized" in lowered
            or "forbidden" in lowered
        ):
            return "auth_error"
        if "429" in lowered or "rate" in lowered:
            return "rate_limit"
        if "policy" in lowered or "safety" in lowered or "content_filter" in lowered:
            return "policy_block"
        if (
            "urlopen error" in lowered
            or "connection" in lowered
            or "name or service not known" in lowered
        ):
            return "network_error"
        return "unknown"

    def _format_validation_errors(self, exc: ValidationError) -> list[str]:
        errors: list[str] = []
        for item in exc.errors():
            loc = ".".join([str(part) for part in item.get("loc", [])])
            msg = str(item.get("msg", "validation error"))
            errors.append(f"{loc}: {msg}" if loc else msg)
        return errors

    def _fatal_result(
        self,
        config: LLMRuntimeConfig | None,
        failure_type: str,
        error: str,
        raw_output: str = "",
        repair_attempts: int = 0,
        validation_errors: list[str] | None = None,
    ) -> LLMStructuredResult:
        cfg = config or LLMRuntimeConfig()
        status = "needs_user_input" if failure_type == "policy_block" else "fatal_error"
        return LLMStructuredResult(
            status=status,
            parsed_output=None,
            validation_errors=validation_errors or [],
            raw_output=raw_output,
            repair_attempts=repair_attempts,
            confidence=None,
            failure_type=failure_type,
            model=cfg.model,
            provider=cfg.provider,
            protocol=cfg.protocol,
            latency_ms=0,
            error=error,
        )

    def _retryable_result(
        self,
        failure_type: str,
        raw_output: str,
        error: str,
        repair_attempts: int,
        validation_errors: list[str] | None = None,
    ) -> LLMStructuredResult:
        return LLMStructuredResult(
            status="retryable_error",
            parsed_output=None,
            validation_errors=validation_errors or [],
            raw_output=raw_output,
            repair_attempts=repair_attempts,
            confidence=None,
            failure_type=failure_type,
            model="",
            provider="",
            protocol="",
            latency_ms=0,
            error=error,
        )
