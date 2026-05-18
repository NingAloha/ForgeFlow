# ForgeFlow Runtime v0.2 Walkthrough

本篇是一个 **可复验** 的 v0.2 walkthrough：验证 “First Governed Materialization” 已经成立。

目标不是开启真实 mutation，而是证明 runtime 能在 **受限边界** 内触达现实，并做到：

- 受治理（gated）
- 可回放（replayable）
- 可审计（auditable）
- 严格受限（writes scoped）

本篇只覆盖一次成功路径；failure semantics（failed/partial/retry）属于 v0.2.1+。

## Materialization attempt lifecycle（v0.2.1+）

v0.2.1 将 materialization preview 视为一次 **attempt lifecycle**，并定义稳定语义：

- `started`：attempt 已开始但未闭合（incomplete attempt）。这是一种 **blocker**，会阻断后续 materialization attempts，避免语义歧义。
- `failed`：attempt 已闭合为失败（signal only）。这是 **可恢复失败**，允许再次 `--materialize-preview` 进行 retry。
- `completed`：attempt 已闭合为成功（terminal success）。再次 `--materialize-preview` 必须是 **幂等 no-op**。

重要边界（语义澄清）：

- materialization preview 是 **governed preview write-path**：只在受限路径内写入 preview artifacts，用于证明 runtime governance 成立。
- materialization preview **不是 mutation**：不改用户源码、不做 patch apply、不执行 mutation，也不引入自动恢复/后台重试语义。

## v0.2 的关键边界

- **Forbidden**：改用户源码、git working tree mutation、自动 patch apply、自动 commit、unrestricted shell execution。
- **Allowed writes**：仅允许写入 `.forgeflow/generated/<run_id>/`（当前只 materialize `README.md`）。
- **Truth vs intent**：
  - `summary.json` / `events.jsonl` / `lineage.json` / `review_state.json` 是 run-scoped truth artifacts。
  - `execution_request.json` / `execution_preview.json` 是 run-scoped intent / preview artifacts。
- **Review decision vs execution approval**：
  - `review_state.json` 的 `pending → approved` 是 artifact review decision（人类评审决策），不是 execution approval。
  - `approvals/*.json`（execution approval artifacts）仍与 mutation 执行语义绑定；v0.2 仍不开放 mutation。

## Step 0 — 准备 fresh runtime root（避免旧 run 污染）

旧 run 中残留的 `pending review` 可能污染 gate signal。建议用 `--state-dir` 指向新的目录来做干净验证：

```bash
export FF_STATE_DIR=/tmp/forgeflow_v02_demo/.forgeflow/state
```

后续所有命令都带 `--state-dir "$FF_STATE_DIR"`。

## Step 1 — 生成一个 run（产出 lineage + review queue）

按仓库根目录 `README.md` 的 quickstart 跑一次 orchestration（示例）：

```bash
python3.11 main.py --state-dir "$FF_STATE_DIR" --auto-run "<your requirement>"
```

找到新 run 的 `run_id`（目录名）：

```bash
ls "$(dirname "$FF_STATE_DIR")/runs"
```

下文用 `<run_id>` 代指这个目录名。

## Step 2 — 确认 review queue 为 pending

检查：

```bash
cat "$(dirname "$FF_STATE_DIR")/runs/<run_id>/review_state.json"
```

期望存在 5 个 lineage artifacts 且为 `pending`：

- `spec`
- `solution`
- `system_design`
- `implementation_status`
- `test_report`

## Step 3 — 写入 review decision（pending → approved）

以下命令写入的是 **review decision**（artifact review），不是 execution approval：

```bash
python3.11 main.py --state-dir "$FF_STATE_DIR" --review-run <run_id> --review-artifact spec --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --state-dir "$FF_STATE_DIR" --review-run <run_id> --review-artifact solution --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --state-dir "$FF_STATE_DIR" --review-run <run_id> --review-artifact system_design --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --state-dir "$FF_STATE_DIR" --review-run <run_id> --review-artifact implementation_status --review-approve --review-by "<id>" --review-reason "<reason>"
python3.11 main.py --state-dir "$FF_STATE_DIR" --review-run <run_id> --review-artifact test_report --review-approve --review-by "<id>" --review-reason "<reason>"
```

## Step 4 — 生成 execution request（intent artifact）

`execution_request.json` 是 materialization 的必要前置（intent），但不代表执行发生：

```bash
python3.11 main.py --state-dir "$FF_STATE_DIR" --request-execution --run-id <run_id> --requested-by "<id>" --notes "<notes>"
```

检查：

```bash
ls "$(dirname "$FF_STATE_DIR")/runs/<run_id>/execution_request.json"
```

## Step 5 — Gate eligibility split：materialization eligible / mutation ineligible

```bash
python3.11 main.py --state-dir "$FF_STATE_DIR" --execution-gate --run-id <run_id>
```

期望看到：

- `eligible_for_materialization: true`
- `eligible_for_mutation: false`

注意：v0.2 仍严格保持 mutation disabled（即使 materialization eligible）。

## Step 6 — Materialize sandbox preview（First Governed Materialization）

执行（write-path；但写入严格受限）：

```bash
python3.11 main.py --state-dir "$FF_STATE_DIR" --materialize-preview --run-id <run_id>
```

期望写入：

- `.forgeflow/generated/<run_id>/README.md`
- `.forgeflow/runs/<run_id>/execution_preview.json`
- `.forgeflow/runs/<run_id>/events.jsonl`（追加 materialization events）

检查：

```bash
cat "$(dirname "$FF_STATE_DIR")/generated/<run_id>/README.md"
cat "$(dirname "$FF_STATE_DIR")/runs/<run_id>/execution_preview.json"
```

## Step 7 — Replay 解释 materialization（可回放证据闭环）

```bash
python3.11 main.py --state-dir "$FF_STATE_DIR" --replay-run <run_id>
```

期望输出包含：

- Timeline 中的 materialization events
- `Materialization:` 段落：
  - `generated_root`
  - `writes`
  - `status`

## What This Proves (v0.2)

在不开放真实 mutation 的前提下，ForgeFlow 已完成：

`review approved + execution request + materialization gate`  
→ `sandbox-scoped preview write`  
→ `execution_preview recorded + events appended`  
→ `replay can explain what was materialized`
