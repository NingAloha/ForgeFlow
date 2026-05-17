# Contributing

## What ForgeFlow currently is

ForgeFlow is a structured AI workflow runtime. ForgeFlow SE is its first target profile.

ForgeFlow Runtime v0 stabilizes the control-plane semantics; the execution engine is intentionally absent
(mutation disabled by design).

## Development workflow

Install (editable):

```bash
python3.11 -m pip install -e ".[dev]"
```

Common commands:

```bash
python3.11 main.py --auto-run "<requirement>"
python3.11 main.py --status
python3.11 main.py --replay --run-id <run_id>
```

## Branch contract model

- `main` is updated via PRs only.
- `track/*` is the primary development branch model: one branch = one runtime contract.
- Keep PR scope small and explicit. Do not mix unrelated contracts.
- Branch scope is enforced by CI. See `docs/branch-boundaries.md`.

## Quality checks

Run these locally before opening a PR:

```bash
ruff check .
pytest -q
```

## PR expectations

- Use a contract-centric title (e.g., `docs: ...`, `runtime: ...`, `ci: ...`).
- State the invariant(s) you are introducing or strengthening.
- Add or update tests when behavior changes.
- For docs changes, keep vocabulary stable and do not blur the truth vs intent boundary.
- Merge, then delete the branch.

## Current runtime boundary (v0)

Keep this section short: it exists to avoid accidental scope expansion.

- Source-of-truth artifacts: `summary.json`, `events.jsonl`, `lineage.json`, `review_state.json`,
  `approvals/*.json`.
- Intent artifacts: `execution_request.json`, `rerun_plan.json` (intent is not factual truth).
- `--enable-mutation` is gate diagnostics only (blocked / not implemented).
- Mutation is disabled by design; do not add workspace mutation in v0 PRs.
