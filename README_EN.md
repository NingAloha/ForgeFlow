# ForgeFlow

ForgeFlow is a contract-driven engineering system centered around Contracts, Artifacts, Verification, and Revisions.

It is not intended to be a generic autonomous AI coding agent.

ForgeFlow is closer to:

```text
User Intent
→ progressive specification
→ semantic stabilization
→ verifiable implementation
```

Each layer acts as a semantic sieve:

- filtering ambiguous requirements
- exposing hidden assumptions
- rejecting inconsistent structures
- preventing unverifiable implementations

Only sufficiently stabilized artifacts are allowed to move forward.

---

# Core Philosophy

Traditional agent systems often collapse because:

- agent boundaries drift
- workflow semantics become unclear
- runtimes turn into orchestration black boxes
- retries introduce semantic drift
- hidden assumptions accumulate silently

Eventually the system reaches a state where:

```text
it appears to function,
but nobody can precisely explain its semantics
```

ForgeFlow attempts to avoid this collapse through:

- explicit artifacts
- explicit contracts
- explicit ownership
- explicit assumptions
- explicit failure attribution
- explicit revision history

---

# System Structure

ForgeFlow operates as a layered semantic filtering system.

```text
User Intent
  ↓
Requirements Sieve
  ↓
Design Sieve
  ↓
Test Sieve
  ↓
Implementation Sieve
  ↓
Verification Sieve
```

Each layer:
- consumes artifacts
- validates semantic consistency
- emits more stabilized artifacts

The core of ForgeFlow is not:
- workflow orchestration
- autonomous agents

The core is:

```text
artifact stabilization
```

---

# Core Ontology

## RequirementSpec

A structured representation of user intent.

Contains:

- goals
- functional requirements
- constraints
- acceptance criteria
- unresolved items
- assumptions

A RequirementSpec must be sufficiently specified before entering the Design stage.

---

## ModuleContract

A behavioral contract for a module.

Defines:

- input format
- input domain
- processing semantics
- output format
- rejection conditions

Does NOT define:

- file structure
- function names
- algorithms
- runtime details
- library choices

Those belong to the implementation world.

---

## ContractGraph

A graph describing relationships between module contracts.

Defines:

- module dependencies
- data flow
- compatibility constraints
- integration expectations

---

## TestSuite

Contract-derived module tests.

Validates:

- input/output behavior
- rejection behavior
- semantic expectations

---

## IntegrationTestSuite

Cross-module integration tests.

Validates:

- contract compatibility
- integration correctness
- cross-module behavior

---

## VerificationResult

A structured verification result.

Contains:

- passed tests
- failed tests
- semantic verification status
- coverage information

---

## FailureReport

A structured failure attribution artifact.

ForgeFlow forbids blind retries.

Every failure must first be attributed:

```yaml
attribution:
  - implementation_error
  - test_error
  - contract_error
  - requirement_error
```

Rollback is only allowed after attribution.

---

## Assumption

An explicit assumption artifact.

ForgeFlow does not allow hidden assumptions.

All:
- inferred defaults
- guessed constraints
- unresolved behaviors

must become explicit artifacts.

---

# Agents

Agents in ForgeFlow are not personality-driven autonomous entities.

They are better understood as:

```text
constrained artifact transformers
```

---

## RequirementsAgent

Transforms:

```text
User Intent
→ RequirementSpec
```

Responsibilities:

- identify ambiguous requirements
- request clarification
- expose unresolved items
- generate assumptions when necessary

Cannot:

- generate implementations
- define contracts
- decide architecture

---

## DesignAgent

Transforms:

```text
RequirementSpec
→ ModuleContracts + ContractGraph
```

Responsibilities:

- define module boundaries
- generate module contracts
- define integration structure

Owns:

- contract ownership
- graph ownership

---

## TestAgent

Transforms:

```text
ModuleContract
→ Module TestSuite
```

Responsibilities:

- generate contract-driven tests
- validate rejection behavior
- preserve semantic expectations

Cannot modify contracts.

---

## IntegrationAgent

Transforms:

```text
ContractGraph
→ Integration TestSuite
```

Responsibilities:

- validate module interoperability
- validate integration correctness

Cannot modify contracts.

---

## ImplementAgent

Transforms:

```text
Contracts + Tests
→ Source Code
```

Responsibilities:

- implement behavior satisfying contracts
- continuously run tests during implementation

Cannot modify:
- contracts
- tests

---

# Runtime

ForgeFlow Runtime is:

```text
a controlled artifact state machine
```

It is NOT:

- an autonomous orchestrator
- a reasoning engine
- an AI planner

Responsibilities:

- invoke agents
- enforce write permissions
- manage state transitions
- run tests
- manage rollbacks
- generate git commits
- preserve revision history

---

# Git

In ForgeFlow, Git is not merely version control.

Git acts as a:

```text
semantic revision ledger
```

Every meaningful transition must produce a revision:

- requirement revisions
- contract revisions
- test generation
- implementation iterations
- verification failures

---

# Failure Handling

ForgeFlow forbids:

```text
failure
→ infinite retry
→ random mutation
```

Correct flow:

```text
failure
→ FailureReport
→ Attribution
→ Precise rollback
```

Example:

```text
Implementation fails
→ implementation_error
→ retry implementation

Tests inconsistent with contract
→ test_error
→ regenerate tests

Contract impossible to satisfy
→ contract_error
→ rollback to DesignAgent

Requirement itself contradictory
→ requirement_error
→ rollback to RequirementsAgent
```

---

# Minimal Project Layout

```text
project/
├── requirements/
│   └── requirement_spec.yaml
│
├── modules/
│   ├── parser/
│   │   ├── contract.yaml
│   │   ├── tests/
│   │   ├── src/
│   │   └── verification/
│   │
│   └── summarizer/
│       ├── contract.yaml
│       ├── tests/
│       ├── src/
│       └── verification/
│
├── integration/
│   ├── contract_graph.yaml
│   ├── tests/
│   └── verification/
│
├── revisions/
│
└── runtime/
```

---

# Current Focus

ForgeFlow is currently focused on:

- ontology stabilization
- contract refinement
- artifact semantics
- verification structure
- revision discipline

ForgeFlow is intentionally avoiding:

- opaque autonomous orchestration
- unconstrained code generation
- hidden reasoning systems
- semantic drift

The most important question for ForgeFlow is not:

```text
Can AI automatically write code?
```

The real question is:

```text
Can software engineering become
stable,
verifiable,
rollbackable,
and semantically traceable?
```