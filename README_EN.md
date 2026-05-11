# ForgeFlow

> NOTE:
> The Chinese README (`README.md`) is currently the primary source of truth during active development.
> This English document is a lightweight developer-oriented overview.

## Overview
ForgeFlow is a structured-state software engineering pipeline with staged progression:
`Requirements -> Solution -> Design -> Implementation -> Testing`.

ForgeShell is the primary UI target, while the CLI runner is the current development/debug entrypoint.

## Architecture

```text
ForgeShell (Primary UI) ─┐
                         ├── Project Orchestrator
CLI Runner (Dev / Debug) ┘
                             ├── State Manager
                             ├── Requirements Engineer
                             ├── Solution Engineer
                             ├── System Designer
                             ├── Implementation Engineer
                             └── Test & Validation Engineer
```

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
