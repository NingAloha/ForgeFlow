# `IMPLEMENTATION` Backflow

`IMPLEMENTATION` 阶段的主判断输入是 `implementation_status.json`，并结合 `system_design.json`、`solution.json` 与 `spec.json` 判断当前阻塞是否仍可在实现层解决。

留在 `IMPLEMENTATION` 的情况：

* `implementation_status` 为 `in_progress`，且没有上游前提失效信号。
* `implementation_status` 为 `blocked`，但 `blockers` 主要是环境、依赖、工具链、权限或资源等执行性问题。
* `contract_compliance = false`，但根因明确是当前实现尚未补完，而 `system_design.contracts` 本身足够清晰。

回流到 `DESIGN`：

* `blockers` 或已知问题直接指向 `system_design` 中 contract、data_flow 或 project_structure 的缺口。
* 当前问题不能仅通过补代码解决，必须先补充或修正 design。
* 当前阻塞可以明确表述为“设计没把交接边界说清楚”。

回流到 `SOLUTION`：

* 根因已经超出 design 细化层，表现为方案层模块承接关系、职责划分或关键技术主干不成立。
* 不先调整 `solution.module_mapping` 或 `selected_stack`，design 与 implementation 都无法稳定继续。
* 当前阻塞可以明确表述为“方案主干不成立，而不是设计没写细”。

回流到 `REQUIREMENTS`：

* 继续实现会直接建立在错误需求前提上。
* 根因直接指向 `spec` 中需求目标、约束或验收标准不稳定。
* `acceptance_criteria` 缺失、`constraints` 冲突，或 `open_questions` 仍阻塞实现。

判断原则：

* `implementation_status = blocked` 不自动等于回流；关键在于 `blockers` 是否说明上游前提失效。
* `contract_compliance = false` 也不自动等于回 `DESIGN`；如果只是实现暂未满足既有 contract，仍应留在 `IMPLEMENTATION`。
