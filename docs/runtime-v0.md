# ForgeFlow Runtime v0

ForgeFlow Runtime v0 定义为：**runtime control plane closed loop**。
它让运行时状态与决策可观测、可审计、可回放；
但 **execution engine 刻意缺席**，mutation **disabled by design**。

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

Phase F 才会引入 controlled apply（执行引擎），并优先限定写入边界到 sandbox 或
`.forgeflow/generated/`（仍不触用户项目源码，除非另立 contract）。

## Runtime Artifacts Model (Truth vs Intent)

v0 将 artifacts 分为两类：**Source-of-truth** 与 **cache/intent**。
其中 intent artifacts 只表达“意图/计划”，不得被当作事实真相。

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
- `--enable-mutation` 是 gate diagnostics（blocked / not implemented），用于渲染诊断；
  退出码 0 表示诊断渲染成功，而不是执行成功。

## Minimal Review Decision Walkthrough (Pre v0.2 Bridge)

本节给出一个最小可复验的 walkthrough，用于验证 v0.1 control plane 可以被“review 向前推进”：
`review_state.json` 能从 `pending → approved`（artifact review decision），并且 `--execution-gate`
的诊断 reasons 会相应减少。

三个关键检查点：

1. `review_state.json` 的 `pending → approved` 是 **review decision**（artifact review），不是 execution approval。
2. `approvals/*.json` 仍然是 **execution approval artifacts**；因此 `--execution-gate` 中 `no_approvals`
   仍可能存在（且 mutation 仍稳定 blocked / not implemented）。
3. 旧 run 的 `pending reviews` 可能污染 gate signal；要做“干净验证”，建议使用 **fresh runtime root**
   （新的 `.forgeflow/`）或确保旧 runs 的 pending 已被清理/隔离。

### Step A — Prepare a fresh runtime root

推荐做法（择一即可）：

- 在一个干净的 workspace path 下运行（没有历史 `.forgeflow/`）。
- 或者临时将 `--state-dir` 指向一个新的位置（如果你本地入口支持 `--state-dir`），确保生成新的 `.forgeflow/`。
- 可选（谨慎）：如果你确认可以丢弃历史诊断数据，可以先移走/清空旧的 `.forgeflow/runs/`。

### Step B — Produce a run that materializes review items

按仓库根目录 `README.md` 的 quickstart 运行一次正常 orchestration（避免在此重复命令），然后在
`.forgeflow/runs/<run_id>/` 中找到对应的 `run_id`（即目录名）。

### Step C — Confirm pending review items exist

打开 `.forgeflow/runs/<run_id>/review_state.json`，期望看到 5 个 lineage artifacts 的 review 状态为 `pending`：

- `spec`
- `solution`
- `system_design`
- `implementation_status`
- `test_report`

### Step D — Approve artifacts (review decision write-path)

以下命令写入的是 **review decision**（artifact review），用于将单个 artifact 标记为 `approved`：

```bash
python3.11 main.py --review-run <run_id> --review-artifact spec --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --review-run <run_id> --review-artifact solution --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --review-run <run_id> --review-artifact system_design --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --review-run <run_id> --review-artifact implementation_status --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --review-run <run_id> --review-artifact test_report --review-approve --review-by "<id>" --review-reason "<reason>"
```

### Step E — Re-check gate diagnostics

```bash
python3.11 main.py --execution-gate
```

期望变化（在 fresh runtime root 的前提下更清晰）：

- `pending_reviews` 应显著减少（或归零）。
- 如果 `needs_rerun` 仅由 pending reviews 驱动，则也会相应减少。
- `no_approvals` 仍可能存在（这是正确的：execution approval artifacts 仍未引入）。

### (Optional) Step F — Materialize intent artifacts

如果你想进一步验证“闭环链路可落盘”，可以 materialize intent artifacts（不代表执行）：

```bash
python3.11 main.py --rerun-plan --run-id <run_id>
python3.11 main.py --request-execution --run-id <run_id> --requested-by "<id>" --notes "<notes>"
```

These commands materialize intent artifacts only.
They do not perform mutation, patch application, or execution.
