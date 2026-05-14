# Branch Boundaries

This file defines branch-to-path ownership for active development tracks.
Use it together with CI guard rules.

## Tracks

### `track/orchestrator`
- Allowed:
  - `agents/orchestrator/**`
  - `tests/unit/orchestrator/**`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- Disallowed:
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/implementation-governance`
- Allowed:
  - `agents/implementation_engineer/**`
  - `tests/unit/agents/test_implementation_engineer.py`
  - `tests/unit/agents/test_execution_*.py`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- Disallowed:
  - `agents/orchestrator/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/testing-semantics`
- Allowed:
  - `agents/test_validation_engineer/**`
  - `tests/unit/agents/test_test_validation_engineer.py`
  - `tests/unit/agents/test_agent_integration.py`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- Disallowed:
  - `agents/orchestrator/**`
  - `agents/implementation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/tui-observability`
- Allowed:
  - `tui/**`
  - `tests/unit/entrypoints/test_tui.py`
  - `agents/orchestrator/**` (read-only query API related changes only)
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- Disallowed:
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `schemas/**`

### `track/docs-review`
- Allowed:
  - `README.md`
  - `README_EN.md`
  - `docs/**`
  - `runs/manual_reviews/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- Disallowed:
  - `agents/**`
  - `tui/**`
  - `tests/**`
  - `schemas/**`

## Rules

- `main` should be merged via PR only.
- CI must pass `ruff check .`, `pytest -q`, and branch path guard.
- If a change requires cross-track edits, split into separate PRs.
