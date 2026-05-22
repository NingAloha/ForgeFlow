# ForgeFlow

> NOTE:
> The Chinese README (`README.md`) is currently the primary source of truth during active development.
> This English document is a lightweight developer-oriented overview.

> TL;DR  
> ForgeFlow is a stateful orchestration runtime for AI software engineering workflows.  
> It emphasizes reproducibility, structural stability, and verifiable process boundaries,  
> not replacing coding agents themselves.

## Overview
The primary failure mode in AI coding is often not code generation itself, but workflow instability:

- non-replayable workflows
- implicit stage drift
- unstable artifact semantics
- unverifiable execution boundaries

ForgeFlow targets this problem space: it treats AI software engineering as a stateful, replayable, verifiable process rather than a sequence of prompts.

ForgeShell is the primary UI target, while the CLI runner is the current development/debug entrypoint.

## Positioning
- ForgeFlow does not replace coding agents; it provides a reproducible orchestration runtime around them.
- ForgeFlow assumes uncontrolled workflow flexibility eventually becomes engineering instability.

## Principles
- Explicit workflow semantics over implicit agent behavior
- Runtime semantics first, capability expansion second
- Fail closed over silent fallback

## Guarantees (Current, Verifiable)
- explicit stages
- artifact contracts
- replayable runs
- lineage visibility
- governed mutation boundaries

## Non-Goals (Current)
- uncontrolled autonomy
- execution mutation enablement in the current phase
- immediate declarative migration of all runtime decisions
- positioning as "another agent framework"

## Current Scope (v0.2.x)

### Completed (Phase-1 decoupling loop)
- PR1: SE workflow facts are declared in the manifest
- PR2: Orchestrator agent binding is manifest-driven
- PR3: runtime lineage dependencies are manifest-driven
- PR4: profile/runtime decoupling boundary is documented

### Intentionally Out of Scope Now
- No `StageEvaluator` refactor yet
- No backflow / question flow declarative migration yet
- No execution mutation enablement (still blocked)

### Next Single Milestone (Not started)
- PR5: declared forward transitions read path
- Acceptance target: behavior-preserving change + green `pytest -q`

- ForgeFlow is not a full replacement for end-to-end autonomous coding systems.
- The current emphasis is structural stability and verifiability of workflow semantics.
- ForgeFlow SE is the first target profile.

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

## System Components
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

## Runtime Model
ForgeFlow is runtime-first: it prioritizes governed runtime semantics (replayability, auditability, boundaries)
before enabling autonomous execution.

- **Core Runtime**: converges control-plane semantics such as replay, lineage, approvals, and execution boundaries.
- **Profiles**: define domain workflows; ForgeFlow SE is the first profile (software engineering pipeline).
- **Skills**: localized, swappable operational capabilities that profiles rely on for concrete actions.

Further reading:
- [docs/runtime-theory.en.md](./docs/runtime-theory.en.md)
- [docs/runtime-theory.md](./docs/runtime-theory.md)

### Capability Boundary Matrix
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

## Runtime Principles
- State is explicit.
- Replay is read-only.
- Events are append-only.
- Execution is governed.
- Runtime artifacts are auditable.
- Human approval is first-class.

## Installation

```bash
python3.11 -m pip install -e ".[dev]"
```

## Developer Workflow

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

## More Documentation
- Runtime root / materialized cache / runtime artifact boundary: `docs/runtime-v0-architecture.md`
- Branch collaboration boundary: `docs/branch-boundaries.md`, `docs/git-workflow.md`
- Execution governance and reviewable execution contracts: `docs/implementation-governance.md`
- Profile/runtime decoupling boundary: `docs/profile-runtime.md`
