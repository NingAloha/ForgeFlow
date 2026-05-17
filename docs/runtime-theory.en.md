# ForgeFlow Runtime Theory

> This document describes the evolving runtime model and architectural direction
> of ForgeFlow Runtime v0.
>
> Some sections describe implemented runtime semantics, while others describe
> possible future runtime directions.

---

# 1. Runtime Beyond the SE Pipeline

ForgeFlow originally started as a staged software engineering pipeline:

```text
Requirements → Solution → Design → Implementation → Testing
```

Over time, the system semantics evolved beyond a software engineering pipeline
into a more general runtime model.

In ForgeFlow Runtime v0:

- ForgeFlow Core is the runtime governance layer
- ForgeFlow SE is the first domain profile

This changes the system definition from:

> “an AI software engineering pipeline”

to:

> “a governed AI workflow runtime”

The primary problem ForgeFlow attempts to solve is no longer:

> “how to make AI generate software”

but instead:

> “how to govern AI interaction with reality through structured runtime contracts”

---

# 2. Core / Profile / Skill

ForgeFlow is converging toward a three-layer runtime architecture.

## 2.1 Core Runtime

The Core Runtime is responsible for runtime governance semantics.

Examples include:

- state management
- replay
- lineage
- approvals
- events
- mutation gates
- rerun semantics
- runtime artifacts

The Core Runtime defines how AI systems interact with reality in a controlled,
auditable, and replayable way.

The Core Runtime is domain-independent.

---

## 2.2 Profiles

Profiles define domain-specific workflow grammars.

The first profile is:

```text
ForgeFlow SE
```

A profile may define:

- stages
- artifact contracts
- dependency semantics
- review semantics
- workflow structure

Profiles describe how a domain organizes work.

They do not define runtime governance itself.

---

## 2.3 Skills

Skills define concrete capabilities.

Examples include:

- Git interaction
- patch generation
- search
- pytest execution
- file materialization

Skills are not workflows.

Skills are localized operational capabilities used by profiles and runtime actors.

---

# 3. Profile Actors and Runtime Separation

The original engineering agents:

- Requirements Engineer
- Solution Engineer
- System Designer
- Implementation Engineer
- Test Validation Engineer

are no longer treated as the runtime itself.

Instead, they are increasingly interpreted as:

```text
ForgeFlow SE profile actors
```

This distinction is important.

The runtime governs execution semantics, while profile actors operate inside
runtime contracts.

This separates:

- workflow governance
from:
- domain-specific task execution

---

# 4. Artifactized Runtime Memory

ForgeFlow Runtime v0 increasingly treats memory as structured runtime artifacts
instead of hidden prompt context.

Examples include:

- `events.jsonl`
- `summary.json`
- `lineage.json`
- `review_state.json`
- `approvals/*.json`
- `rerun_plan.json`
- `execution_request.json`

These artifacts collectively form:

```text
runtime operational memory
```

This differs from systems primarily based on:

- vector memory
- long prompt memory
- scratchpad memory

ForgeFlow instead favors:

- structured operational memory
- replayable artifacts
- explicit lineage
- governed state transitions

The runtime therefore depends less on hidden conversational context and more on
materialized semantic state.

---

# 5. Patch-Scoped Development

A major runtime direction emerging from ForgeFlow Runtime v0 is
patch-scoped development.

Traditional agent systems often require a single agent to understand large
amounts of project context simultaneously.

This creates:

- context explosion
- token inefficiency
- cache instability
- weak replayability
- poor parallelism

ForgeFlow instead moves toward:

```text
runtime + artifacts + contracts + lineage
```

This enables work to be decomposed into governed patches.

In this model, an actor does not need to understand the entire project.

The runtime only needs to provide:

- relevant artifacts
- relevant contracts
- dependency state
- allowed file scope
- invariant tests

This reduces dependence on large global context windows.

The problem therefore shifts from:

> “how to make one agent understand the whole system”

to:

> “how to decompose reality into governed runtime patches”

This is a significant architectural shift.

---

# 6. Tree-Based Readiness and Invalidation

ForgeFlow originally used a largely linear rollback model:

```text
Testing failure
→ rollback to Implementation
→ rollback to Design
```

A possible future runtime direction is a semantic dependency tree model.

In this model:

- readiness propagates through dependency graphs
- invalidation propagates through downstream nodes
- execution depends on dependency readiness

This may eventually replace large parts of linear orchestration logic.

Possible future semantics include:

- readiness propagation
- invalidation propagation
- dependency gating
- tree-scoped rerun planning

This would allow:

```text
tree state → workflow progression
```

instead of:

```text
central orchestration intelligence → workflow progression
```

This section describes a possible future runtime direction and is not fully
implemented in Runtime v0.

---

# 7. Git as Substrate, Not Replacement

ForgeFlow does not attempt to replace Git.

Instead:

```text
Git = storage and history substrate
ForgeFlow = runtime semantics layer
```

Future runtime-governed Git interaction may include:

- gated mutation
- replayable changes
- branch-scoped execution
- governed patch application

Current runtime principles include:

- `main` remains protected
- mutation must remain gated
- `track/*` branches represent isolated runtime contracts
- Git interaction should initially remain read-only or sandboxed

ForgeFlow therefore treats Git as foundational infrastructure rather than as an
implementation detail to bypass.

---

# 8. Governed Mutation

Runtime v0 primarily implemented:

```text
execution governance semantics
```

rather than autonomous execution capability.

Implemented runtime semantics include:

- replay
- lineage
- approvals
- truth vs intent separation
- rerun semantics
- governed execution boundaries
- runtime artifacts

Execution is therefore increasingly treated as a governed runtime contract.

---

# 9. Runtime v0 and v0.2 Direction

Runtime v0 establishes the control-plane semantics of ForgeFlow.

The next major validation target is not “stronger AI”, but instead:

```text
governed materialization
```

Possible future runtime validation targets include:

- sandbox writes
- controlled apply
- replayable mutation
- gated execution
- branch-scoped changes

The primary goal is to validate execution semantics under runtime governance.

The objective is not unrestricted autonomy.

---

# 10. Runtime Direction

ForgeFlow is increasingly transitioning from:

```text
prompt-driven agent systems
```

toward:

```text
contract-driven runtime systems
```

The primary objective is no longer:

> “making agents behave more like humans”

Instead, ForgeFlow attempts to make AI interaction with reality:

- governable
- replayable
- auditable
- approval-aware
- partially invalidatable
- patch-scoped
- contract-driven

This direction increasingly defines the architectural identity of ForgeFlow
Runtime.