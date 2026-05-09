# ForgeFlow / ForgeShell

A multi-agent software engineering pipeline driven by structured state.

## Overview

ForgeFlow turns a user request into a staged engineering flow:

* Requirements
* Solution
* Design
* Implementation
* Testing

ForgeShell is the target primary user-facing entrypoint for this flow. The currently runnable entrypoint in this repository is `main.py`, a minimal CLI runner for development, debugging, smoke tests, and orchestration checks with diagnostic output (`one-shot` or `--auto-run`).

## What This Project Is

This is not a general chat application.

It is a workflow-oriented engineering system built around:

* layered agents that each own one stage of work
* a control layer that routes the workflow
* structured state files used as stage contracts
* an interaction layer where TUI is the target product entrypoint and CLI is the currently runnable development/debug entrypoint

## Architecture Snapshot

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

## Core Ideas

* Separation of concerns: each agent owns one layer
* Contract-driven flow: stages hand off structured outputs
* Implicit orchestration: normal usage should feel automatic
* Explicit control: users can still inspect, switch, lock, and intervene
* State transparency: the system should expose progress without unnecessary noise

## Repository Layout

```text
forgeflow/
├── docs/
├── agents/
├── schemas/
├── state/
├── tui/
├── main.py
└── README.md
```

Directory guide:

* [README.md](../README.md): Chinese-first project entry
* [README.md in docs](./README.md): documentation index
* [agents/README.md](../agents/README.md): agent and control-layer responsibilities
* [state/README.md](../state/README.md): state contract examples and field reference
* [schemas/README.md](../schemas/README.md): runtime schema layer and state validation registry
* [main.py](../main.py): minimal CLI runner for one-shot or `--auto-run` orchestration and diagnostic reporting
* [tui/README.md](../tui/README.md): ForgeShell terminal UI layer
* LLM key resolution precedence: `api_key` (or `FORGEFLOW_LLM_API_KEY`) first, then the value from the env var named by `api_key_env` (default `DEEPSEEK_API_KEY`)

## Documentation Map

Recommended reading order:

1. [Chinese README](../README.md)
2. [docs/README.md](./README.md)
3. [workflow docs](./workflow/README.md)
4. [state docs](./state/README.md)

## Current Scope

Current MVP direction:

* ForgeShell as the target primary interaction entrypoint (current runnable path is still CLI diagnostics)
* a minimal CLI runner for development and diagnostics
* automatic role orchestration
* visible workflow state
* a single-thread flow from requirements to testing
* JSON-backed stage state management
* runtime state stored under `.forgeflow/state/` by default

## Status

Current repository state:

* workflow stage criteria have been drafted in `docs/`
* state JSON contracts have been tightened and documented
* module-level README files have been added for navigation
* `main.py` can now trigger one-shot orchestration or run continuously with `--auto-run`, and print per-step diagnostic reports
* the requirements stage can now produce the first structured `spec` fields and raise blocking clarification questions when needed
* the solution stage can now derive an initial `selected_stack`, `module_mapping`, `risks`, and `alternatives` from the current `spec`
* `question_state = answered` now routes execution back to the owning stage so answers can be consumed instead of remaining stuck in a waiting state
* state payloads are now validated through Pydantic schemas during state load/save
* invalid state payload fallback is observable through diagnostic `state_validation_errors`
* runtime state now defaults to `.forgeflow/state/` so repository contract examples stay clean
* implementation stage currently represents implementation planning/status, not automatic code generation
* implementation is still early-stage
