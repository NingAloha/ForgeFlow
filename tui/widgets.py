from __future__ import annotations

from agents.orchestrator import Stage


def render_status_bar(final_stage: Stage | str, decision_type: str) -> str:
    return f"[ForgeShell] 阶段={final_stage} 决策={decision_type}"


def render_input_hint() -> str:
    return "命令: /status /open spec /open solution /open design /run /help /quit"
