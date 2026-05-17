# Docs

这里放项目文档索引。根目录 `README.md` 只保留项目入口和高层导航。

按主题阅读：

1. [workflow/README.md](./workflow/README.md)
2. [state/README.md](./state/README.md)
3. [agents/README.md](./agents/README.md)
4. [entrypoints/README.md](./entrypoints/README.md)
5. [git-workflow.md](./git-workflow.md)
6. [runtime-v0-architecture.md](./runtime-v0-architecture.md)
7. [runtime-v0.md](./runtime-v0.md)

## Runtime Semantics Notes

- [runtime-theory.md](./runtime-theory.md)
- [runtime-theory.en.md](./runtime-theory.en.md)

如果你想从代码目录职责入手，再看：

* [../agents/README.md](../agents/README.md)
* [../state/README.md](../state/README.md)
* [../schemas/README.md](../schemas/README.md)
* [../tui/README.md](../tui/README.md)

## ForgeFlow Runtime v0: Control Plane Closed Loop

ForgeFlow Runtime v0 已形成 **runtime control plane 的闭环**，
但 **execution engine 刻意缺席**（mutation disabled by design）。

闭环链路：

`status → replay → events → run index → lineage → review/approval → rerun plan → execution request → mutation gate`

### What Phase A–E Completed

- **Phase A**: narrative convergence（将 ForgeFlow 统一为 “AI workflow runtime”，ForgeFlow SE 作为第一个 profile）
- **Phase B**: `.forgeflow/runs/index.json`（materialized cache index；index is cache, not source of
  truth；status 优先读 index，必要时 fallback scan）
- **Phase C**: `.forgeflow/runs/<run_id>/lineage.json`（lineage metadata foundation）
- **Phase D**: review/approval semantics（run-scoped `review_state.json` + read-only queue / aggregation）
- **Phase E**: intent artifacts + gate diagnostics（`execution_request.json` / `rerun_plan.json` +
  mutation gate / `--enable-mutation` 仍 blocked / not implemented）

### Mutation Status

- 当前 mutation **disabled by design**。
- `--enable-mutation` 只是 **gate diagnostic**（render diagnostics，即使 blocked 也返回退出码 0），不是执行入口。
- Phase F 才进入 controlled apply（优先 sandbox / `.forgeflow/generated/`，不触用户项目源码）。

### Runtime Artifacts (v0)

本节将 runtime artifacts 分为两类：**Source-of-truth artifacts** 与
**Materialized cache / intent artifacts**。其中 intent artifacts 只表达 “意图/计划”，不是事实真相。

**Source-of-truth artifacts**

- `.forgeflow/runs/<run_id>/summary.json`
- `.forgeflow/runs/<run_id>/events.jsonl`
- `.forgeflow/runs/<run_id>/lineage.json`
- `.forgeflow/runs/<run_id>/review_state.json`
- `.forgeflow/runs/<run_id>/approvals/*.json`

**Materialized cache / intent artifacts**

- `.forgeflow/runs/index.json`（cache）
- `.forgeflow/runs/<run_id>/rerun_plan.json`（intent）
- `.forgeflow/runs/<run_id>/execution_request.json`（intent）

### Continue Reading

- [runtime-status.md](./runtime-status.md)
- [runtime-events.md](./runtime-events.md)
- [branch-boundaries.md](./branch-boundaries.md)
- [entrypoints/README.md](./entrypoints/README.md)
