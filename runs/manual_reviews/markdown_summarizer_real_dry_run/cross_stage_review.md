## Cross-Stage Pipeline Review (Phase 23)

### Current Pipeline Shape
`Requirements -> Solution -> Design -> Implementation -> Testing -> Orchestrator -> TUI`

### Stage Consumption Map
- Requirements -> Solution:
  - `spec.functional_requirements` feeds `solution.module_mapping[*].covers_requirements`.
  - Risk/alternative fields remain consumable but still depend on requirement text quality.
- Solution -> Design:
  - `solution.module_mapping` maps to `system_design.project_structure.modules`.
  - Design contracts and data-flow reference solution-driven module ownership.
- Design -> Implementation:
  - Implementation handoff consumes `project_structure.modules`, `contracts`, `data_flow`, and `mvp_plan`.
  - Output is checklist/governance-focused, not code mutation.
- Implementation -> Testing:
  - Testing consumes handoff readiness (`implementation_status=done`, blockers empty, alignment true).
  - Execute-path governance artifacts remain review-only; they do not trigger mutation.

### Orchestrator Explainability Review
- Forward decisions now include explicit “downstream consumable” evidence.
- Stay decisions now include missing-invariant evidence (for example blockers/alignment gaps).
- Wait decisions now include explicit “progress paused until blocking question resolved”.
- No-progress guard remains structured and records `stop_reason`, repeated stage/decision, and step index in run summary.

### TUI Observability Review
- `/status` remains read-only and now exposes:
  - current stage/decision
  - question status
  - implementation mode signal (`handoff`/`execute` heuristic)
  - approval artifact presence
  - apply plan presence
  - mutation enabled flag (`no`)
- No new control commands were added.

### Execution Governance Summary
- Supported and reviewable:
  - execution contract
  - contract validation
  - approval semantics + artifact draft
  - approval-aware gate
  - dry-run apply plan + apply plan validation
- Not enabled:
  - real mutation runtime
  - patch apply
  - command execution

### Current Non-Goals
- No file mutation in execute path.
- No command execution in execute path.
- No schema/state-machine expansion for governance artifacts.
- No new CLI/TUI execution control surface.

### Weakest Stage Now
- **Solution text quality under low-quality requirement extraction**:
  - downstream structure is stable, but semantic precision still depends on upstream requirement phrasing.

### Next Architectural Risk
- **Cross-stage semantic drift risk**:
  - execution governance artifacts are rich, but upstream requirement granularity can still produce noisy module semantics that propagate through solution/design into handoff/testing evidence.
