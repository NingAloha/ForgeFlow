from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


RuntimeEventType = Literal[
    "run_started",
    "decision_computed",
    "stage_executed",
    "run_finished",
    "materialization_preview_started",
    "materialization_preview_written",
    "materialization_preview_finished",
]


@dataclass(slots=True)
class RuntimeEvent:
    timestamp: str
    event_type: RuntimeEventType
    run_id: str
    sequence: int
    payload: dict[str, Any]


@dataclass(slots=True)
class RuntimeEventLog:
    events: list[RuntimeEvent]
    errors: list[dict[str, Any]]


def _utc_timestamp_z() -> str:
    # UTC ISO8601 with Z suffix.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _events_path(run_dir: Path) -> Path:
    return run_dir / "events.jsonl"


def load_runtime_events(run_dir: Path) -> RuntimeEventLog:
    path = _events_path(run_dir)
    if not path.exists():
        return RuntimeEventLog(events=[], errors=[])

    events: list[RuntimeEvent] = []
    errors: list[dict[str, Any]] = []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append({"line_no": 0, "raw": "", "reason": f"read_failed: {exc}"})
        return RuntimeEventLog(events=[], errors=errors)

    for idx, raw in enumerate(lines, start=1):
        text = raw.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(
                {"line_no": idx, "raw": raw, "reason": f"invalid_json: {exc}"}
            )
            continue
        if not isinstance(payload, dict):
            errors.append(
                {"line_no": idx, "raw": raw, "reason": "invalid_payload: not_object"}
            )
            continue

        timestamp = payload.get("timestamp")
        event_type = payload.get("event_type")
        run_id = payload.get("run_id")
        sequence = payload.get("sequence")
        event_payload = payload.get("payload", {})

        if not isinstance(timestamp, str):
            errors.append(
                {"line_no": idx, "raw": raw, "reason": "invalid_field: timestamp"}
            )
            continue
        if event_type not in {
            "run_started",
            "decision_computed",
            "stage_executed",
            "run_finished",
            "materialization_preview_started",
            "materialization_preview_written",
            "materialization_preview_finished",
        }:
            errors.append(
                {"line_no": idx, "raw": raw, "reason": "invalid_field: event_type"}
            )
            continue
        if not isinstance(run_id, str) or not run_id.strip():
            errors.append({"line_no": idx, "raw": raw, "reason": "invalid_field: run_id"})
            continue
        try:
            seq_int = int(sequence)
        except (TypeError, ValueError):
            errors.append({"line_no": idx, "raw": raw, "reason": "invalid_field: sequence"})
            continue
        if seq_int < 1:
            errors.append({"line_no": idx, "raw": raw, "reason": "invalid_field: sequence_range"})
            continue
        if not isinstance(event_payload, dict):
            errors.append(
                {"line_no": idx, "raw": raw, "reason": "invalid_field: payload"}
            )
            continue

        events.append(
            RuntimeEvent(
                timestamp=timestamp,
                event_type=event_type,  # type: ignore[arg-type]
                run_id=run_id.strip(),
                sequence=seq_int,
                payload=event_payload,
            )
        )

    # Keep file order; additionally surface non-monotonic sequence as errors.
    last_seq = 0
    for event in events:
        if event.sequence <= last_seq:
            errors.append(
                {
                    "line_no": 0,
                    "raw": "",
                    "reason": f"sequence_not_monotonic: {event.sequence} after {last_seq}",
                }
            )
            break
        last_seq = event.sequence

    return RuntimeEventLog(events=events, errors=errors)


def append_runtime_event(
    run_dir: Path,
    event_type: RuntimeEventType,
    run_id: str,
    payload: dict[str, Any] | None = None,
) -> RuntimeEvent:
    path = _events_path(run_dir)
    payload_dict = payload or {}

    log = load_runtime_events(run_dir)
    max_sequence = 0
    for event in log.events:
        if event.sequence > max_sequence:
            max_sequence = event.sequence
    next_sequence = max_sequence + 1 if max_sequence else 1

    event = RuntimeEvent(
        timestamp=_utc_timestamp_z(),
        event_type=event_type,
        run_id=str(run_id).strip(),
        sequence=next_sequence,
        payload=payload_dict,
    )

    line = json.dumps(
        {
            "timestamp": event.timestamp,
            "event_type": event.event_type,
            "run_id": event.run_id,
            "sequence": event.sequence,
            "payload": event.payload,
        },
        ensure_ascii=False,
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return event
