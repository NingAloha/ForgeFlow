from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExecutionRequest:
    schema_version: str
    run_id: str
    requested_at: str
    requested_by: str
    requested_capability: str
    notes: str


def ensure_safe_run_id(run_id: str) -> str:
    rid = str(run_id).strip()
    if not rid:
        raise ValueError("run_id must be non-empty")
    if "/" in rid or "\\" in rid:
        raise ValueError("run_id must not contain path separators")
    if ".." in rid:
        raise ValueError("run_id must not contain traversal segments")
    return rid


def execution_request_path(runs_root: Path, run_id: str) -> Path:
    rid = ensure_safe_run_id(run_id)
    return runs_root / rid / "execution_request.json"


def write_execution_request(
    *,
    runs_root: Path,
    run_id: str,
    requested_by: str,
    notes: str,
) -> Path:
    rid = ensure_safe_run_id(run_id)
    run_dir = runs_root / rid
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"run directory not found: {run_dir}")

    payload = {
        "schema_version": "1",
        "run_id": rid,
        "requested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requested_by": str(requested_by).strip(),
        "requested_capability": "controlled_execution",
        "notes": str(notes).strip(),
    }

    path = run_dir / "execution_request.json"
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return path


def load_execution_request(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}

