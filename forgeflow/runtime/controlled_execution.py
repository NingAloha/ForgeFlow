from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .execution_gate import build_execution_gate_snapshot, render_execution_gate
from .execution_request import load_execution_request


PHASE_F_PREREQUISITES = [
    "patch apply",
    "rollback",
    "conflict handling",
    "partial write recovery",
    "dirty worktree protection",
    "sandbox boundary",
    "user project ownership",
]


@dataclass(slots=True)
class ControlledExecutionResult:
    output: str


def render_controlled_execution_blocked(
    *,
    state_dir: Path,
    run_id: str,
    require_request_present: bool = True,
) -> ControlledExecutionResult:
    run_dir = state_dir.parent / "runs" / str(run_id).strip()
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")

    request_path = run_dir / "execution_request.json"
    request_present = request_path.exists()
    if require_request_present and not request_present:
        raise FileNotFoundError(f"execution request not found: {request_path}")
    _ = load_execution_request(request_path) if request_present else {}

    gate = build_execution_gate_snapshot(state_dir=state_dir)
    lines: list[str] = []
    lines.append("ForgeFlow Controlled Execution")
    lines.append("Status: blocked (not implemented)")
    lines.append(f"Run ID: {str(run_id).strip()}")
    lines.append(f"Execution request present: {request_present}")
    lines.append("")
    lines.append(render_execution_gate(gate))
    lines.append("")
    lines.append("Phase F prerequisites:")
    for item in PHASE_F_PREREQUISITES:
        lines.append(f"- {item}")

    return ControlledExecutionResult(output="\n".join(lines))

