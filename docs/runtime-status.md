# Runtime Status (Read-only)

ForgeFlow 的 runtime 不是“输入 -> 输出”，而是 stateful workflow runtime。为了让系统可解释自己处于什么状态，本分支新增只读观测入口：

```bash
python3.11 main.py --status
python3.11 main.py --status --state-dir <path-to-state-dir>
```

## 只读边界
- 不改变 orchestrator transition 逻辑（不修改 `decide_next_stage()` / `resolve_transition()` 语义）。
- 不写入或修改任何 state/artifact（不创建新的 run 目录，不生成 project dir）。
- 不改变 implementation 的 patch preview / execution / mutation / sandbox 语义。
- 不改变 testing attribution（implementation vs structure vs contract）。

## 字段语义（概览）
- `current_stage`: 基于 `resolve_transition(states).final_stage` 的只读决策结果。
- `executed_stage`: 来自最新存在的 `runs/<run_id>/summary.json` 的最后一步 `executed_stage`（若无 summary 则为空）。
- `next_stage`: 来自决策的 `next_stage_to_execute`（若无则为 `None`）。
- `artifacts`: 以 state json 文件是否存在作为 availability（存在即 `available`）。
- `mutation_enabled`: 固定为 `false`（观测字段）。
- `execution_mode`: 固定为 `preview-only`（观测字段）。
- `blockers`: 只读汇总（blocking question、implementation blockers、state validation errors、testing 高危 issues）。

## 复用入口
- `forgeflow/runtime/status.py`: `build_status_snapshot(...)` 统一状态读取与汇总（只读）。
- `forgeflow/runtime/render.py`: `render_status(...)` 负责渲染输出（无 IO）。
