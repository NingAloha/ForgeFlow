# `SOLUTION` Backflow

`SOLUTION` 阶段的主判断输入是 `solution.json`，并结合 `spec.json` 判断当前方案是尚未收紧，还是已经暴露出 requirements 前提不成立。

留在 `SOLUTION` 的情况：

* `selected_stack` 尚未完全补齐，但关键技术位已有清晰方向。
* `module_mapping` 还在细化，但核心需求已经有基本承接关系。
* `risks` 或 `alternatives` 仍在补充，但不影响当前形成稳定方案主干。

回流到 `REQUIREMENTS`：

* 当前方案无法稳定收敛成可进入 design 的主干。
* 根因直接指向 `spec` 中需求目标、验收标准、约束或范围边界不稳定。
* `module_mapping` 无法稳定回答“哪些模块承接哪些需求”，或者 `selected_stack` 无法收敛。

判断原则：

* `selected_stack` 某些字段为空，不自动等于回流；关键在于方案主干是否还能稳定承接需求。
* solution 阶段不能通过主观假设替代关键需求澄清。
