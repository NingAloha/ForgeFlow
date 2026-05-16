from __future__ import annotations

from .status import RuntimeStatus


def _as_label(value: str | None) -> str:
    text = (value or "").strip()
    return text if text else "None"


def render_status(status: RuntimeStatus) -> str:
    lines: list[str] = []
    lines.append("ForgeFlow Status")
    lines.append(f"Stage: {status.current_stage}")
    lines.append(f"Executed Stage: {_as_label(status.executed_stage)}")
    lines.append(f"Next Stage: {_as_label(status.next_stage)}")

    lines.append("Artifacts")
    for key in sorted(status.artifacts):
        label = "available" if status.artifacts[key] else "missing"
        lines.append(f"- {key}: {label}")

    lines.append("Execution")
    lines.append(f"- mutation: {'enabled' if status.mutation_enabled else 'disabled'}")
    lines.append(f"- execution: {status.execution_mode}")

    if status.lineage_entries:
        lines.append("Lineage")
        for item in status.lineage_entries:
            artifact = str(item.get("artifact", "")).strip() or "unknown"
            depends_on = item.get("depends_on", [])
            if not isinstance(depends_on, list):
                depends_on = []
            generated_by = str(item.get("generated_by", "")).strip() or "unknown"
            lines.append(f"- {artifact}: depends_on={depends_on} generated_by={generated_by}")

    if status.last_decision:
        lines.append("Last Decision")
        action = status.last_decision.get("action", "").strip() or "unknown"
        target = status.last_decision.get("final_stage", "").strip() or "unknown"
        lines.append(f"- action: {action}")
        lines.append(f"- target: {target}")

    lines.append("Blockers")
    if status.blockers:
        for item in status.blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    return "\n".join(lines)
