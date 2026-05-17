# ForgeFlow Runtime v0

ForgeFlow Runtime v0 定义为：**runtime control plane closed loop**。它让运行时状态与决策可观测、可审计、可回放；但 **execution engine 刻意缺席**，mutation **disabled by design**。

（架构闭环图见：[`docs/runtime-v0-architecture.md`](./runtime-v0-architecture.md)）

## Invariants (v0)

- State is explicit.
- Replay is read-only.
- Events are append-only.
- Execution is governed.
- Runtime artifacts are auditable.
- Human approval is first-class.

## Non-goals (v0)

- 不做 patch apply / 不做真实落盘执行。
- 不写用户项目源码（不在用户工作区做 mutation）。
- 不做自动 rerun（`rerun_plan.json` 仅为 intent / diagnostics）。
- 不做 DAG scheduler / auto orchestration based on dependency graph。

## Phase F Boundary (Controlled Apply)

Phase F 才会引入 controlled apply（执行引擎），并优先限定写入边界到 sandbox 或 `.forgeflow/generated/`（仍不触用户项目源码，除非另立 contract）。

## Runtime Artifacts Model (Truth vs Intent)

v0 将 artifacts 分为两类：**Source-of-truth** 与 **cache/intent**。其中 intent artifacts 只表达“意图/计划”，不得被当作事实真相。

**Source-of-truth artifacts**

- `.forgeflow/runs/<run_id>/summary.json`
- `.forgeflow/runs/<run_id>/events.jsonl`
- `.forgeflow/runs/<run_id>/lineage.json`
- `.forgeflow/runs/<run_id>/review_state.json`
- `.forgeflow/runs/<run_id>/approvals/*.json`

**Materialized cache / intent artifacts**

- `.forgeflow/runs/index.json`（materialized cache；may lag behind truth）
- `.forgeflow/runs/<run_id>/rerun_plan.json`（intent）
- `.forgeflow/runs/<run_id>/execution_request.json`（intent）

## CLI Semantics (v0)

- 所有写入命令必须显式指定 `--run-id <run_id>`（不会默认 latest）。
- `--enable-mutation` 是 gate diagnostics（blocked / not implemented），用于渲染诊断；退出码 0 表示诊断渲染成功，而不是执行成功。
