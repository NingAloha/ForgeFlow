from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


LineageArtifact = Literal[
    "spec",
    "solution",
    "system_design",
    "implementation_status",
    "test_report",
]


@dataclass(slots=True)
class LineageEntry:
    artifact: str
    depends_on: list[str]
    generated_by: str
    invalidated_by: list[str]


@dataclass(slots=True)
class LineageMetadata:
    schema_version: str
    run_id: str
    entries: list[LineageEntry]


def _lineage_path(run_dir: Path) -> Path:
    return run_dir / "lineage.json"


def depends_on_for_artifact(artifact: LineageArtifact) -> list[str]:
    if artifact == "spec":
        return []
    if artifact == "solution":
        return ["spec"]
    if artifact == "system_design":
        return ["solution"]
    if artifact == "implementation_status":
        return ["system_design"]
    if artifact == "test_report":
        return ["implementation_status"]
    return []


def load_lineage(run_dir: Path) -> LineageMetadata | None:
    path = _lineage_path(run_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    schema_version = str(payload.get("schema_version", "")).strip()
    run_id = str(payload.get("run_id", "")).strip()
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        return None

    entries: list[LineageEntry] = []
    for item in raw_entries:
        if not isinstance(item, dict):
            return None
        artifact = str(item.get("artifact", "")).strip()
        depends_on = item.get("depends_on", [])
        generated_by = str(item.get("generated_by", "")).strip()
        invalidated_by = item.get("invalidated_by", [])
        if not isinstance(depends_on, list) or not isinstance(invalidated_by, list):
            return None
        entries.append(
            LineageEntry(
                artifact=artifact,
                depends_on=[str(x).strip() for x in depends_on if str(x).strip()],
                generated_by=generated_by,
                invalidated_by=[str(x).strip() for x in invalidated_by if str(x).strip()],
            )
        )

    return LineageMetadata(schema_version=schema_version, run_id=run_id, entries=entries)


def upsert_lineage_entry(
    *,
    run_dir: Path,
    run_id: str,
    artifact: LineageArtifact,
    generated_by: str,
) -> None:
    existing = load_lineage(run_dir)
    entries: list[LineageEntry] = [] if existing is None else list(existing.entries)

    by_artifact: dict[str, LineageEntry] = {item.artifact: item for item in entries if item.artifact}
    by_artifact[str(artifact)] = LineageEntry(
        artifact=str(artifact),
        depends_on=depends_on_for_artifact(artifact),
        generated_by=str(generated_by).strip(),
        invalidated_by=[],
    )
    merged = list(by_artifact.values())
    merged.sort(key=lambda item: item.artifact)

    payload = {
        "schema_version": "1",
        "run_id": str(run_id).strip(),
        "entries": [
            {
                "artifact": item.artifact,
                "depends_on": item.depends_on,
                "generated_by": item.generated_by,
                "invalidated_by": item.invalidated_by,
            }
            for item in merged
        ],
    }

    path = _lineage_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)

