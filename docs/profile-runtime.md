# Profile Runtime Boundary (v0.2.x)

This document captures the **current decoupling boundary** between ForgeFlow Core runtime and the Software Engineering (SE) profile.

It is a boundary/contract note, **not** a roadmap and **not** a design proposal.

---

## What SE Manifest Declares (Facts / Contracts)

The SE profile manifest declares the following facts:

- profile `name` / `version`
- `stages` (stage identifiers and order)
- `artifact_keys` (the SE profile's public artifact contract surface)
- stage → agent mapping (`stage_agents`, dotted import paths)
- stage → produced artifact mapping (`stage_produces`)
- forward stage chain (`transitions`, declared fact only)
- artifact dependency declaration for lineage (`lineage_dependencies`)

---

## What Runtime Consumes Today

The manifest is currently consumed only on the explicitly listed surfaces below:

- **PR2**: Orchestrator consumes `stage_agents` via the profile registry to bind stage actors (agent instances).
- **PR3**: Runtime lineage consumes `lineage_dependencies` via the profile registry as the dependency **source-of-truth** for lineage metadata.

**Important (anti-misread):**

*The current manifest is not yet the source of truth for all runtime decisions. It is the source of truth only for the explicitly listed consumption surfaces.*

中文：

manifest 还不是所有 runtime 决策的唯一真相源；它只对当前列出的消费面负责。

---

## What Remains Intentionally Hardcoded (Not Yet Declared)

The following components are intentionally **not** driven by the manifest yet:

- `StageEvaluator` readiness criteria and the boolean-chain stage truth model
- backflow resolution rules
- question flow semantics (awaiting user / blocking behavior)
- execution / mutation semantics (still blocked by design)

---

## Why Transition Decision Is Not Declarative Yet

Transition decision and stage evaluation are the most sensitive runtime truth sources.
Declaring them prematurely would risk changing:

- forward/hold/backflow behavior
- failure modes (fail-closed vs silent fallback)
- regression coverage and offline reproducibility assumptions

Therefore, v0.2.x focuses on **contract extraction and safe read paths** first (manifest/registry/lineage),
and keeps decision logic unchanged until the boundary is fully stabilized and guarded.

---

## Invariants / Acceptance (v0.2.x)

- Changes must be **behavior-preserving** (no stage decision drift).
- Unknown contracts should **fail closed**.
- Execution remains **blocked** (no patch apply / command execution).
- `pytest -q` remains the baseline regression gate.

