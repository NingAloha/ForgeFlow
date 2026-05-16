from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


RunIndexStatus = Literal["running", "finished", "unknown"]
RunIndexLoadStatus = Literal["ok", "missing", "invalid"]


@dataclass(slots=True)
class RunIndexEntry:
    run_id: str
    created_at: str
    finished_at: str
    summary_path: str
    events_path: str
    final_stage: str
    status: RunIndexStatus


@dataclass(slots=True)
class RunIndex:
    runs: list[RunIndexEntry]


@dataclass(slots=True)
class RunIndexLoadResult:
    status: RunIndexLoadStatus
    index: RunIndex | None
    error: str | None = None


def _index_path(runs_root: Path) -> Path:
    return runs_root / "index.json"


def _parse_created_at_from_run_id(run_id: str) -> str:
    match = re.match(r"^(?P<prefix>\d{8}T\d{6}Z)-", str(run_id).strip())
    if not match:
        return ""
    prefix = match.group("prefix")
    try:
        parsed = datetime.strptime(prefix, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_index_entry(
    *,
    run_id: str,
    final_stage: str = "",
    status: RunIndexStatus = "unknown",
    finished_at: str = "",
) -> RunIndexEntry:
    rid = str(run_id).strip()
    created_at = _parse_created_at_from_run_id(rid)
    normalized_status: RunIndexStatus = status
    if not created_at:
        normalized_status = "unknown"
    return RunIndexEntry(
        run_id=rid,
        created_at=created_at,
        finished_at=str(finished_at).strip(),
        summary_path=f"{rid}/summary.json",
        events_path=f"{rid}/events.jsonl",
        final_stage=str(final_stage).strip(),
        status=normalized_status,
    )


def load_run_index(runs_root: Path) -> RunIndex | None:
    result = load_run_index_result(runs_root)
    return result.index


def load_run_index_result(runs_root: Path) -> RunIndexLoadResult:
    path = _index_path(runs_root)
    if not path.exists():
        return RunIndexLoadResult(status="missing", index=None)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RunIndexLoadResult(status="invalid", index=None, error="invalid_json")
    if not isinstance(payload, dict):
        return RunIndexLoadResult(status="invalid", index=None, error="not_a_dict")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return RunIndexLoadResult(status="invalid", index=None, error="runs_not_a_list")

    entries: list[RunIndexEntry] = []
    for item in runs:
        if not isinstance(item, dict):
            return RunIndexLoadResult(status="invalid", index=None, error="run_entry_not_a_dict")
        try:
            entry = RunIndexEntry(
                run_id=str(item.get("run_id", "")).strip(),
                created_at=str(item.get("created_at", "")).strip(),
                finished_at=str(item.get("finished_at", "")).strip(),
                summary_path=str(item.get("summary_path", "")).strip(),
                events_path=str(item.get("events_path", "")).strip(),
                final_stage=str(item.get("final_stage", "")).strip(),
                status=str(item.get("status", "")).strip(),  # type: ignore[arg-type]
            )
        except Exception:
            return RunIndexLoadResult(status="invalid", index=None, error="run_entry_invalid_shape")
        if entry.status not in {"running", "finished", "unknown"}:
            return RunIndexLoadResult(status="invalid", index=None, error="run_entry_invalid_status")
        if not entry.run_id or not entry.summary_path:
            return RunIndexLoadResult(status="invalid", index=None, error="run_entry_missing_required_fields")
        entries.append(entry)

    return RunIndexLoadResult(status="ok", index=RunIndex(runs=entries))


def update_index_on_run_event(
    *,
    runs_root: Path,
    event_type: Literal["run_started", "run_finished", "stage_executed"],
    run_id: str,
    final_stage: str = "",
    finished_at: str = "",
) -> None:
    if event_type == "run_started":
        entry = build_index_entry(run_id=run_id, status="running", final_stage="", finished_at="")
    elif event_type == "run_finished":
        entry = build_index_entry(
            run_id=run_id,
            status="finished",
            final_stage=final_stage,
            finished_at=finished_at,
        )
    else:
        # Keep stage-executed updates minimal for v1: do not attempt to infer
        # completion or rewrite finished timestamps. The index is a cache and may
        # lag behind; status/replay must remain correct via fallback scan.
        entry = build_index_entry(run_id=run_id, status="running", final_stage=final_stage, finished_at="")
    update_run_index(runs_root, entry)


def materialize_run_index_from_runs_root(runs_root: Path) -> RunIndex:
    """
    Build a best-effort index from the filesystem (source of truth: run dirs).

    This function is intentionally read-only: it does not write index.json.
    """
    entries: list[RunIndexEntry] = []
    if not runs_root.exists():
        return RunIndex(runs=[])

    for summary_path in runs_root.glob("*/summary.json"):
        run_id = summary_path.parent.name
        final_stage = ""
        finished_at = ""
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = None
        if isinstance(payload, dict):
            final_stage = str(payload.get("latest_final_stage", "")).strip()
            steps = payload.get("steps", [])
            if isinstance(steps, list) and steps and isinstance(steps[-1], dict):
                finished_at = str(steps[-1].get("timestamp", "")).strip()

        entries.append(
            build_index_entry(
                run_id=run_id,
                status="unknown",
                final_stage=final_stage,
                finished_at=finished_at,
            )
        )

    entries.sort(key=_sort_key, reverse=True)
    return RunIndex(runs=entries)


def _sort_key(entry: RunIndexEntry) -> tuple[int, int, str, str, str]:
    # Sort descending:
    # 1) valid created_at first (created_at != "")
    # 2) finished first
    # 3) valid created_at: by created_at desc
    # 4) finished_at desc (break same-second created_at ties for finished runs)
    # 5) invalid created_at: by run_id desc
    valid = 1 if entry.created_at else 0
    finished = 1 if entry.status == "finished" else 0
    created_at_or_id = entry.created_at if entry.created_at else entry.run_id
    finished_at = entry.finished_at if entry.finished_at else ""
    return (valid, finished, created_at_or_id, finished_at, entry.run_id)


def update_run_index(runs_root: Path, entry: RunIndexEntry) -> None:
    existing = load_run_index(runs_root)
    runs: list[RunIndexEntry] = [] if existing is None else list(existing.runs)

    by_id: dict[str, RunIndexEntry] = {item.run_id: item for item in runs if item.run_id}
    by_id[entry.run_id] = entry
    merged = list(by_id.values())
    merged.sort(key=_sort_key, reverse=True)

    path = _index_path(runs_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "run_id": item.run_id,
                        "created_at": item.created_at,
                        "finished_at": item.finished_at,
                        "summary_path": item.summary_path,
                        "events_path": item.events_path,
                        "final_stage": item.final_stage,
                        "status": item.status,
                    }
                    for item in merged
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def write_run_index(runs_root: Path, index: RunIndex) -> None:
    """
    Write index.json as an atomic rewrite.

    Callers must treat index as a cache: it is not a source of truth.
    """
    entries = list(index.runs)
    entries.sort(key=_sort_key, reverse=True)

    path = _index_path(runs_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "run_id": item.run_id,
                        "created_at": item.created_at,
                        "finished_at": item.finished_at,
                        "summary_path": item.summary_path,
                        "events_path": item.events_path,
                        "final_stage": item.final_stage,
                        "status": item.status,
                    }
                    for item in entries
                ]
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)
