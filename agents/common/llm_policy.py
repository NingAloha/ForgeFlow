from __future__ import annotations

from collections.abc import Callable

from ..base import AgentResult, QuestionItem, QuestionState
from .llm_gateway import LLMStructuredResult
from .runtime_config import LLMRuntimeConfig


def should_use_llm(config: LLMRuntimeConfig, stage_name: str) -> bool:
    return config.enabled and stage_name in config.enabled_stages


def build_llm_failure_question_state(stage_name: str, state_key: str, error: str) -> QuestionState:
    message = error.strip() or "LLM generation failed."
    return QuestionState(
        status="awaiting_user",
        stage_name=stage_name,
        state_key=state_key,
        blocking=True,
        created_by=f"{stage_name} agent",
        resolution_summary="",
        questions=[
            QuestionItem(
                id="llm_generation_failure",
                title="LLM generation failed",
                description=message,
                response_type="free_text",
                allow_free_text=True,
            )
        ],
    )


def resolve_gateway_failure(
    *,
    llm_result: LLMStructuredResult,
    llm_config: LLMRuntimeConfig,
    stage_name: str,
    state_key: str,
    agent_name: str,
    updated_state: dict,
    fallback_factory: Callable[[], AgentResult] | None,
    strict_summary: str,
    fatal_summary: str,
) -> AgentResult | None:
    # This helper is only for non-success statuses.
    if llm_result.status == "success":
        return None

    if llm_result.status == "retryable_error":
        if llm_config.execution_mode != "strict_llm" and fallback_factory is not None:
            return fallback_factory()
        if llm_config.execution_mode != "strict_llm":
            return None
        return AgentResult(
            agent_name=agent_name,
            stage_name=stage_name,
            state_key=state_key,
            updated_state=updated_state,
            summary=strict_summary,
            notes=["LLM retry budget exhausted; waiting for user action."],
            blockers=["llm_generation_failed"],
            handoff_ready=False,
            requires_user_input=True,
            question_state_update=build_llm_failure_question_state(
                stage_name,
                state_key,
                llm_result.error,
            ),
            diagnostics={"llm_trace": llm_result.to_trace()},
        )

    if llm_result.status in {"fatal_error", "needs_user_input"}:
        if llm_config.execution_mode != "strict_llm" and fallback_factory is not None:
            return fallback_factory()
        if llm_config.execution_mode != "strict_llm":
            return None
        return AgentResult(
            agent_name=agent_name,
            stage_name=stage_name,
            state_key=state_key,
            updated_state=updated_state,
            summary=fatal_summary,
            notes=["LLM output was invalid or unavailable; waiting for user action."],
            blockers=["llm_generation_failed"],
            handoff_ready=False,
            requires_user_input=True,
            question_state_update=build_llm_failure_question_state(
                stage_name,
                state_key,
                llm_result.error,
            ),
            diagnostics={"llm_trace": llm_result.to_trace()},
        )

    return None
