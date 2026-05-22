# ForgeFlow

> NOTE:
> The Chinese README (`README.md`) is currently the primary source of truth during active development.
> This English document is a lightweight developer-oriented overview.

## Overview
The primary failure mode in AI coding is often not code generation itself, but workflow instability:

- non-replayable workflows
- implicit stage drift
- unstable artifact semantics
- unverifiable execution boundaries

ForgeFlow targets this problem space: it treats AI software engineering as a stateful, replayable, verifiable process rather than a sequence of prompts.

ForgeShell is the primary UI target, while the CLI runner is the current development/debug entrypoint.

## Positioning
- ForgeFlow does not replace coding agents.
- ForgeFlow provides a reproducible orchestration runtime around agents.
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

## Current Focus (v0.2.x)

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

## Scope (Current Boundary)
- ForgeFlow is not a full replacement for end-to-end autonomous coding systems.
- The current emphasis is structural stability and verifiability of workflow semantics.
- ForgeFlow SE is the first target profile.

## Four Concepts (Core / Profile / Skill / Shell)

### ForgeFlow Core
Owns runtime convergence and control-plane semantics:
- orchestration
- runtime
- replay
- governance
- events
- approvals
- state semantics

### ForgeFlow SE (first profile)
Owns staged software engineering artifacts:
- Requirements
- Solution
- Design
- Implementation
- Testing

### ForgeFlow Skills
Owns localized, swappable operational capabilities that profiles rely on for concrete actions.

### ForgeShell
As the human interface (entrypoint) layer, owns human-in-the-loop interaction and inspection:
- human-in-the-loop interaction
- runtime inspection
- approvals
- replay/status

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
- `execute` (disabled preview path): returns blocked status with preview artifacts only.

Current execute-mode status semantics:
- blocked
- patch preview generated
- single-module patch draft generated
- no mutation performed

## Execution Safety Boundary
Real code execution is currently disabled.
Future execution requires safety controls such as:
- sandboxed workspace
- allowed/denied path policy
- allowed command policy
- retry limit
- patch preview
- rollback policy
- execution report

## Patch Preview / Patch Draft
Patch preview and patch draft are dry-run outputs only.

Patch draft constraints in current implementation:
- limited to the first design module
- unified diff preview
- create-only
- README placeholders only
- no Python implementation code generation
- no file writes
- no command execution

## Runtime Artifact Boundary
- Runtime cache artifacts must not be committed:
  - `.forgeflow/state/`
  - `.forgeflow/generated/`
  - `.forgeflow/runs/`
  - non-curated runtime outputs under `runs/*`
  - `/tmp/forgeflow_*` (outside repository scope)
- Repository knowledge that should remain versioned:
  - `runs/manual_reviews/` (curated review artifacts)
- Goal: keep runtime outputs (generated files, run summaries, previews) from polluting repository history.

## Runtime Principles
- State is explicit.
- Replay is read-only.
- Events are append-only.
- Execution is governed.
- Runtime artifacts are auditable.
- Human approval is first-class.

## Runtime Root

The default runtime root is `.forgeflow/`:

```text
.forgeflow/
├── state/
├── runs/
│   ├── <run_id>/
│   │   ├── summary.json
│   │   ├── events.jsonl
│   │   └── approvals/
└── generated/
```

### Materialized runtime artifacts

These artifacts are already present in Runtime v0 (materialized cache; may lag behind truth;
index is cache, not source of truth):

```text
.forgeflow/runs/index.json
```

## Repo metadata suggestions (not applied in this PR)
- GitHub Description:
  - A structured AI workflow runtime. First profile: Software Engineering Pipeline.
- Topics:
  - ai-workflow-runtime
  - llm-orchestration
  - structured-workflow
  - ai-engineering
  - agentic-workflow
  - runtime-governance
- LICENSE:
  - MIT (present)

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

## Branch Collaboration Boundary
- Recommended branch model: `main` (stable trunk) + `track/*` (topic branches).
- `track/*` branches are enforced by a CI branch path guard; out-of-scope file changes fail CI.
- Boundary policy is defined in [docs/branch-boundaries.md](./docs/branch-boundaries.md).
- Guard files:
  - `scripts/branch_path_guard.sh`
  - `.github/workflows/branch-path-guard.yml`

## Current Limitations
- Execute mode is not enabled for real mutation.
- Patch artifacts are previews only and are never applied.
- No real Code Agent execution path is enabled in the stable flow.
