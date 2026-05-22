# ForgeFlow Roadmap

## North Star

ForgeFlow is a runtime-first, artifact-first orchestration system for structured engineering workflows.

The project is not intended to be a prompt chain or a thin wrapper around LLM calls.
Its primary focus is:

- explicit state transitions
- replayable workflow execution
- strict artifact contracts
- offline-testable orchestration
- controlled and inspectable runtime behavior

Software Engineering (SE) is the first profile implemented on top of the runtime, not the final shape of the system itself.

---

# Core Principles

## Runtime First

The runtime governs execution semantics.

Agents are replaceable.
Artifacts and transitions are not.

The orchestration layer must remain stable even when:
- prompts change
- providers change
- models change
- profiles evolve

---

## Artifact First

Artifacts are the primary interface between stages.

Stages communicate through structured contracts rather than implicit prompt memory.

Artifacts must be:
- explicit
- serializable
- versioned
- replayable
- independently validated

---

## Fail Closed

ForgeFlow should refuse unsafe or ambiguous execution rather than guessing.

Examples:
- unknown schema versions fail validation
- invalid transitions do not silently continue
- unsupported execution capabilities remain blocked
- partial runtime corruption should degrade safely

---

## Offline Reproducibility

Core orchestration behavior must be testable without real LLM calls.

Regression infrastructure should rely on:
- fixtures
- fake agents
- deterministic traces
- state snapshots

Real model output is not considered a stable golden baseline.

---

## Controlled Capability Growth

Execution capability must only expand after:
- runtime contracts stabilize
- governance semantics exist
- rollback semantics exist
- isolation boundaries are enforced

Mutation capability is downstream of orchestration maturity, not upstream.

---

# Non-Goals

The project is currently NOT attempting to become:

- a fully autonomous coding agent
- a self-modifying runtime
- an unrestricted shell execution framework
- a benchmark-chasing agent swarm
- a "one prompt builds everything" system

ForgeFlow prioritizes:
- correctness
- inspectability
- governance
- replayability
over raw autonomy.

---

# Current State

Current implementation status:

## Implemented

- staged orchestration runtime
- persistent state management
- replay semantics
- no-op detection
- transition reasoning
- strict Pydantic state validation
- lineage metadata
- offline regression testing
- SE workflow profile
- execution governance semantics
- dry-run / blocked execution contracts

## Intentionally Missing

- patch apply runtime
- real command execution
- uncontrolled filesystem mutation
- sandboxed execution environment
- profile-independent orchestration kernel
- generalized artifact DAG runtime

---

# Roadmap

## v0.2.x — Contract Runtime

Goal:
Transform SE from an implicit runtime shape into the first declared profile.

Focus areas:
- profile manifest system
- profile registry
- orchestrator/profile decoupling
- declared transitions
- declared lineage dependencies
- schema versioning
- migration strategy
- artifact compatibility policy

Explicitly out of scope:
- real mutation
- patch apply
- command execution

Desired outcome:
Core no longer directly depends on SE workflow structure.

---

## v0.3.x — Safe Execution Preview

Goal:
Introduce execution semantics without enabling uncontrolled mutation.

Focus areas:
- patch plan models
- execution intent contracts
- dry-run apply previews
- sandbox boundary abstraction
- rollback metadata
- execution policy layer
- approval semantics

Desired outcome:
ForgeFlow can reason about execution safely before performing execution.

---

## v0.4.x — Controlled Mutation Runtime

Goal:
Enable restricted real execution under governance constraints.

Focus areas:
- approved patch application
- isolated workspace execution
- command policy enforcement
- execution tracing
- test feedback loops
- rollback support
- mutation audit logs

Desired outcome:
Controlled execution becomes possible without abandoning replayability or governance.

---

## v0.5.x — Multi-Profile Runtime

Goal:
Generalize ForgeFlow beyond Software Engineering.

Potential profiles:
- documentation workflows
- learning workflows
- research synthesis
- architecture review
- structured planning systems

Focus areas:
- profile SDK
- profile-scoped artifact contracts
- reusable runtime primitives
- profile lifecycle tooling

Desired outcome:
SE becomes one profile among many rather than the runtime's implicit default.

---

# Long-Term Direction

Long-term, ForgeFlow aims to explore:

- artifact-oriented AI workflows
- governed execution systems
- deterministic orchestration around nondeterministic models
- replayable agent runtimes
- inspectable multi-stage reasoning systems

The project intentionally prioritizes architectural integrity over rapid capability expansion.

---

# Invariants

The following properties should remain true across future versions.

## Runtime Invariants

- transitions are explicit
- state is serializable
- orchestration is replayable
- failures are inspectable
- unknown contracts fail closed

---

## Architecture Invariants

- Core should not implicitly encode profile semantics
- artifacts are the system boundary
- execution capability is policy-gated
- runtime behavior must remain testable offline

---

## Governance Invariants

- mutation requires explicit capability
- approval semantics must remain visible
- replay and auditability must not regress
- execution should always be attributable