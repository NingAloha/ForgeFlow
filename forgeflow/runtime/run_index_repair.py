from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .run_index import RunIndex, materialize_run_index_from_runs_root, write_run_index


@dataclass(slots=True)
class RunIndexRepairResult:
    runs_written: int


def repair_run_index(runs_root: Path) -> RunIndexRepairResult:
    """
    Explicit repair command: rebuild `.forgeflow/runs/index.json` from run directories.

    - Source of truth: run directories (summary.json/events.jsonl)
    - index.json: cache only
    """
    index: RunIndex = materialize_run_index_from_runs_root(runs_root)
    write_run_index(runs_root, index)
    return RunIndexRepairResult(runs_written=len(index.runs))

