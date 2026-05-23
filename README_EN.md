# ForgeFlow

> NOTE:
> The Chinese README (`README.md`) is currently the primary source of truth during active development.
> This English document is a lightweight developer-oriented overview.

> TL;DR  
> ForgeFlow is an **engineering state system** for AI-assisted software development.  
> It makes “where the project is, what’s proven, and what to roll back” inspectable via structured artifacts and runtime evidence, not hidden prompt memory.

## 1. Problem / Failure Model
Modern AI coding agents can make local progress (generate code, fix errors, implement a module),
but they often fail to maintain a stable, inspectable **project engineering state** over long-running work.

Typical failures are engineering-state continuity failures, not prompting failures:
- requirement drift
- pseudo-completion without executable evidence
- broken traceability across requirements/design/implementation/testing
- rollback ambiguity after failures

## 2. What ForgeFlow Is
ForgeFlow is an engineering state system for AI-assisted software development, using staged progression:

```text
Requirements → Solution / Architecture → Design → Implementation → Testing
```

Primary object:
> project engineering state

ForgeFlow is **Git-aware** and is designed to bind engineering state to Git snapshots / recovery points eventually, but it does not treat “completed node → Git commit” as an implemented guarantee today.

## 3. What ForgeFlow Is Not
ForgeFlow is not:
- a general-purpose workflow engine / orchestration framework
- a multi-agent framework (not a LangGraph / CrewAI / AutoGen alternative)
- a prompt chain manager
- a coding agent or a Claude Code replacement

Agents are implementation details: stage state producers, not the primary abstraction.

## 4. Core Model
- Staged progression driven by structured state contracts and evaluator rules.
- Completion is not “LLM says done”; it must be derivable from structured state (schema-valid / structurally complete; traceable where possible).
- Testing failures should map to attribution and rollback targets (partially documented/implemented in this repo; see docs).

## 5. Artifacts and Evidence
Evidence has a strength ladder:
- Soft evidence: LLM review / self-reports (never “verified” by itself)
- Stronger evidence: structured artifacts, lineage/trace links, runtime events, diagnostics, review/approval records
- Harder evidence (when available): real test/command executions and their results

Inspectable artifacts produced today:
- `.forgeflow/state/*.json`: stage state (spec/solution/system_design/implementation_status/test_report/question_state)
- `.forgeflow/runs/<run_id>/`: runtime evidence (`summary.json`, `events.jsonl`, `lineage.json`, `review_state.json`, `approvals/*.json`, …)

## 6. Current guarantees and boundaries
Implemented today:
- structured state contracts + schema validation
- replayable runtime artifacts (events/summary/lineage/review/approvals)
- governed execution boundaries and preview-only execution contracts (mutation disabled by design)

Designed direction (not yet a guarantee):
- stronger evidence binding and attribution semantics
- tighter binding to Git recovery points (checkpoint metadata)

Not yet implemented:
- real mutation runtime (patch apply / command execution)
- automatic rollback

## Architecture

```text
ForgeShell (Primary UI) ─┐
                         ├── Project Orchestrator
CLI Runner (Dev / Debug) ┘
                             ├── State Manager
                             ├── Profile Registry
                             │     └── ForgeFlow SE Manifest
                             │           ├── stage_agents
                             │           ├── stage_produces
                             │           ├── transitions
                             │           └── lineage_dependencies
                             ├── StageEvaluator
                             └── SE Agents (bound via manifest stage_agents)
                                   ├── Requirements Engineer
                                   ├── Solution Engineer
                                   ├── System Designer
                                   ├── Implementation Engineer
                                   └── Test & Validation Engineer
```

Boundary (anti-misread):

*The current manifest is not yet the source of truth for all runtime decisions. It is the source of truth only for the explicitly listed consumption surfaces.*

- Manifest-driven consumption surfaces today:
  - Orchestrator consumes `stage_agents` for agent binding
  - runtime lineage consumes `lineage_dependencies`
- Intentionally not declarative yet: `StageEvaluator` / backflow / question flow / execution

Further reading: `docs/profile-runtime.md`

## System Components (implementation layers)
- **ForgeFlow Core**: converges control-plane semantics (`state` / `events` / `replay` / `governance` / `approvals`)
- **ForgeFlow SE**: first profile defining staged constraints and artifacts for software engineering workflows
- **ForgeFlow Skills**: localized, swappable operational capabilities
- **ForgeShell**: human-in-the-loop interaction and runtime inspection entrypoint

## Entrypoints
Execution routes through the Project Orchestrator for both entrypoints.

Supported commands in the current TUI shell:
- `/status`
- `/open spec`
- `/open solution`
- `/open design`
- `/run`
- `/help`
- `/quit`

Unsupported control commands (not implemented):
- `/rollback`, `/retry`, `/switch`, `/lock`, `/execute`, `/apply`

## Current Capabilities
- One-shot orchestration and `--auto-run` progression are available in `main.py`.
- `--tui` launches the minimal ForgeShell terminal shell.
- Implementation currently produces handoff artifacts and execution previews, not real code mutation.

### Capability Boundary Matrix (verifiable)
| Capability | Status |
| --- | --- |
| Planning (Requirements/Solution/Design) | ✅ |
| Implementation Handoff | ✅ |
| Reviewable Execution Contract | ✅ |
| Approval Semantics | ✅ |
| Dry-run Apply Plan | ✅ |
| Real Mutation Runtime | ❌ |
| Patch Apply | ❌ |
| Command Execution | ❌ |

## Implementation Modes
- `handoff` (default, stable): design-to-implementation checklist output.
- `execute` (preview-only): returns `blocked` plus reviewable execution contract output; no real mutation.

Detailed execution governance semantics are documented in:
- [docs/implementation-governance.md](./docs/implementation-governance.md)
- [docs/profile-runtime.md](./docs/profile-runtime.md)

## 7. Quickstart

```bash
python3.11 -m pip install -e ".[dev]"
```

Developer workflow:

```bash
python3.11 main.py --auto-run "<requirement>"
python3.11 main.py --tui
forgeflow --tui
```

Input note:
- user input is currently positional.
- `--input` is not supported.

Current quality gate:
- `ruff check .`
- `pytest -q`

## Current Limitations
- Execute mode is not enabled for real mutation.
- Patch artifacts are previews only and are never applied.
- No real Code Agent execution path is enabled in the stable flow.

## 8. Docs map
- Runtime root / materialized cache / runtime artifact boundary: `docs/runtime-v0-architecture.md`
- Branch collaboration boundary: `docs/branch-boundaries.md`, `docs/git-workflow.md`
- Execution governance and reviewable execution contracts: `docs/implementation-governance.md`
- Profile/runtime decoupling boundary: `docs/profile-runtime.md`
- Runtime direction notes (implemented vs possible future): `docs/runtime-theory.en.md`
- Workflow rules and backflow docs: `docs/workflow/README.md`
- State contracts entry: `docs/state/README.md`
