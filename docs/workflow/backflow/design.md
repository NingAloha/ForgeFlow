# `DESIGN` Backflow

`DESIGN` 阶段的主判断输入是 `system_design.json`，并结合 `solution.json` 与 `spec.json` 判断当前 design 是否只是未补完，还是已经暴露出上游前提不足。

留在 `DESIGN` 的情况：

* `project_structure.modules`、`contracts`、`data_flow` 或 `mvp_plan` 尚在细化，但核心主干已经能继续补充。
* 当前缺的是 design 细节，而不是重做方案或需求。

回流到 `SOLUTION`：

* 当前 design 无法继续稳定展开，无法形成可指导 implementation 的结构。
* 根因直接指向 `solution` 中技术主干、模块承接关系或职责划分不足。
* 不先调整 solution，`system_design` 无法补成 `DESIGN` 所要求的可实现结构。

回流到 `REQUIREMENTS`：

* 当前 design 无法继续收敛成可实现结构。
* 根因直接指向 `spec` 中需求目标、验收标准、约束或范围边界不稳定。
* `open_questions` 中仍存在会阻塞 contract 定义或主流程闭环的关键问题。

判断原则：

* `contracts` 或 `data_flow` 为空，不自动等于回流；先判断是 design 尚未补完，还是上游前提不足。
* 如果问题体现为“方案不足以支撑 design”，回 `SOLUTION`。
* 如果问题体现为“需求不足以支撑 solution 和 design”，回 `REQUIREMENTS`。
