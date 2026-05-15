from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


RunIndexStatus = Literal["running", "finished", "unknown"]


@dataclass(slots=True)
class RunIndexEntry:
    run_id: str
    created_at: str
    summary_path: str
    events_path: str
    final_stage: str
    status: RunIndexStatus


@dataclass(slots=True)
class RunIndex:
    runs: list[RunIndexEntry]


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
) -> RunIndexEntry:
    rid = str(run_id).strip()
    created_at = _parse_created_at_from_run_id(rid)
    normalized_status: RunIndexStatus = status
    if not created_at:
        normalized_status = "unknown"
    return RunIndexEntry(
        run_id=rid,
        created_at=created_at,
        summary_path=f"{rid}/summary.json",
        events_path=f"{rid}/events.jsonl",
        final_stage=str(final_stage).strip(),
        status=normalized_status,
    )


def load_run_index(runs_root: Path) -> RunIndex | None:
    path = _index_path(runs_root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return None

    entries: list[RunIndexEntry] = []
    for item in runs:
        if not isinstance(item, dict):
            return None
        try:
            entry = RunIndexEntry(
                run_id=str(item.get("run_id", "")).strip(),
                created_at=str(item.get("created_at", "")).strip(),
                summary_path=str(item.get("summary_path", "")).strip(),
                events_path=str(item.get("events_path", "")).strip(),
                final_stage=str(item.get("final_stage", "")).strip(),
                status=str(item.get("status", "")).strip(),  # type: ignore[arg-type]
            )
        except Exception:
            return None
        if entry.status not in {"running", "finished", "unknown"}:
            return None
        if not entry.run_id or not entry.summary_path:
            return None
        entries.append(entry)

    return RunIndex(runs=entries)


def _sort_key(entry: RunIndexEntry) -> tuple[int, int, str, str]:
    # Sort descending:
    # 1) valid created_at first (created_at != "")
    # 2) finished first
    # 3) valid created_at: by created_at desc; invalid: by run_id desc
    valid = 1 if entry.created_at else 0
    finished = 1 if entry.status == "finished" else 0
    time_or_id = entry.created_at if entry.created_at else entry.run_id
    return (valid, finished, time_or_id, entry.run_id)


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
