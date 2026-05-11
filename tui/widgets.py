from __future__ import annotations

from agents.orchestrator import Stage


def render_status_bar(final_stage: Stage | str, decision_type: str) -> str:
    return f"[ForgeShell] stage={final_stage} decision={decision_type}"


def render_input_hint() -> str:
    return "Commands: /status /open spec /open solution /open design /run /help /quit"
