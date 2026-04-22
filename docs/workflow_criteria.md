# Workflow Criteria Reference

这一页只负责介绍工作流判定体系、状态机和规则文档入口。具体的正向进入条件与回流规则，拆分到专门文档中维护，避免入口页承担过多细节。

## State Machine

```text
INIT
→ REQUIREMENTS_READY
→ SOLUTION_READY
→ DESIGN_READY
→ IMPLEMENTING
→ TESTING
→ DONE
```

当前状态机对应的持久化文件为：

* `state/spec.json`
* `state/solution.json`
* `state/system_design.json`
* `state/implementation_status.json`
* `state/test_report.json`

## 文档分工

* [workflow_scope.md](./workflow_scope.md)：当前工作流适用场景与边界，回答“这套规则主要适用于什么，不适用于什么”。
* [workflow_stage_criteria.md](./workflow_stage_criteria.md)：正向阶段进入条件，回答“什么时候可以进入下一阶段”。
* [workflow_backflow_rules.md](./workflow_backflow_rules.md)：回流规则与状态失效处理，回答“什么时候应该退回上游阶段，以及回流后哪些结论失效”。
* [state_contracts.md](./state_contracts.md)：各状态文件的字段契约，回答“每个阶段状态里应该写什么”。

推荐阅读顺序：

1. 当前 `workflow_criteria.md`
2. [workflow_scope.md](./workflow_scope.md)
3. [workflow_stage_criteria.md](./workflow_stage_criteria.md)
4. [workflow_backflow_rules.md](./workflow_backflow_rules.md)
5. [state_contracts.md](./state_contracts.md)

## 快速索引

### 正向推进

| 阶段 | 主判断文件 | 关键问题 |
| --- | --- | --- |
| `REQUIREMENTS_READY` | `state/spec.json` | 需求是否已经足够明确，可以进入方案设计 |
| `SOLUTION_READY` | `state/solution.json` | 方案主干是否已经稳定，可以进入系统设计 |
| `DESIGN_READY` | `state/system_design.json` | 设计是否已经可指导编码落地 |
| `IMPLEMENTING` | `state/implementation_status.json` | 实现动作是否已经正式开始 |
| `TESTING` | `state/test_report.json` | 当前实现是否已经进入可验证状态 |
| `DONE` | `state/test_report.json` | 当前这一轮是否已经完成闭环交付 |

### 回流判断

| 当前阶段 | 主判断文件 | 主要输出 |
| --- | --- | --- |
| `TESTING` | `state/test_report.json` | 留在 `TESTING` 或回流到 `IMPLEMENTING` / `DESIGN_READY` / `SOLUTION_READY` / `REQUIREMENTS_READY` |
| `IMPLEMENTING` | `state/implementation_status.json` | 留在 `IMPLEMENTING` 或回流到 `DESIGN_READY` / `SOLUTION_READY` / `REQUIREMENTS_READY` |
| `DESIGN_READY` | `state/system_design.json` | 留在 `DESIGN_READY` 或回流到 `SOLUTION_READY` / `REQUIREMENTS_READY` |
| `SOLUTION_READY` | `state/solution.json` | 留在 `SOLUTION_READY` 或回流到 `REQUIREMENTS_READY` |

详细字段级判断与回流后状态处理，请直接查看 [workflow_stage_criteria.md](./workflow_stage_criteria.md) 和 [workflow_backflow_rules.md](./workflow_backflow_rules.md)。
