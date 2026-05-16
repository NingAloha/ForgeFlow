from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RuntimePauseState:
    paused: bool
    reason: str


def _pause_path(state_dir: str | Path | None) -> Path:
    base = Path(state_dir) if state_dir is not None else Path.cwd() / ".forgeflow" / "state"
    return base / "runtime_pause.json"


def load_runtime_pause_state(state_dir: str | Path | None = None) -> RuntimePauseState:
    path = _pause_path(state_dir)
    if not path.exists():
        return RuntimePauseState(paused=False, reason="")
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RuntimePauseState(paused=False, reason="")
    if not isinstance(payload, dict):
        return RuntimePauseState(paused=False, reason="")
    paused = bool(payload.get("paused", False))
    reason = str(payload.get("reason", "")).strip()
    return RuntimePauseState(paused=paused, reason=reason)

