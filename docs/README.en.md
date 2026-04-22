# ForgeFlow / ForgeShell

A multi-agent software engineering pipeline with a chat-first TUI.

## Overview

ForgeFlow turns a user request into a staged engineering flow:

* Requirements
* Solution
* Design
* Implementation
* Testing

ForgeShell is the terminal interface for this flow. It provides a chat-style experience while keeping workflow state, role switching, and progress visible.

## What This Project Is

This is not a general chat application.

It is a workflow-oriented engineering system built around:

* layered agents that each own one stage of work
* a control layer that routes the workflow
* structured state files used as stage contracts
* a TUI that exposes progress without forcing the user to manage every step manually

## Architecture Snapshot

```text
User
  ↓
ForgeShell (Chat TUI)
  ↓
Project Orchestrator
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
* [state/README.md](../state/README.md): persisted stage state files
* [schemas/README.md](../schemas/README.md): future formal schema layer
* [tui/README.md](../tui/README.md): ForgeShell terminal UI layer

## Documentation Map

Recommended reading order:

1. [Chinese README](../README.md)
2. [docs/README.md](./README.md)
3. [workflow_criteria.md](./workflow_criteria.md)
4. [state_contracts.md](./state_contracts.md)

## Current Scope

Current MVP direction:

* chat input through ForgeShell
* automatic role orchestration
* visible workflow state
* a single-thread flow from requirements to testing
* JSON-backed stage state management

## Status

Current repository state:

* workflow stage criteria have been drafted in `docs/`
* state JSON contracts have been tightened and documented
* module-level README files have been added for navigation
* implementation is still early-stage
