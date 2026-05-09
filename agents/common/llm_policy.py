from __future__ import annotations

from ..base import QuestionItem, QuestionState
from .runtime_config import LLMRuntimeConfig


def should_use_llm(config: LLMRuntimeConfig, stage_name: str) -> bool:
    return config.enabled and stage_name in config.enabled_stages


def should_block_on_llm_failure(
    config: LLMRuntimeConfig,
    stage_name: str,
    llm_used: bool,
    fallback_used: bool,
) -> bool:
    return (
        config.execution_mode == "strict_llm"
        and should_use_llm(config, stage_name)
        and (not llm_used or fallback_used)
    )


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
