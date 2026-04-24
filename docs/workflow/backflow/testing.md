# `TESTING` Backflow

`TESTING` 阶段的主判断输入是 `test_report.json`，并结合 `implementation_status.json`、`system_design.json`、`solution.json` 与 `spec.json` 判断根因层级。

留在 `TESTING` 的情况：

* `result = not_run`。
* `result = partial`，但现有 `issues` 仍不足以判断根因层级。
* 当前问题只是测试执行不完整、环境暂未就绪或验证范围未收齐。

回流到 `IMPLEMENTATION`：

* `result` 为 `fail` 或 `partial`。
* `issues` 中至少存在一项 `status` 为 `open` 或 `confirmed` 的问题。
* 问题可主要归因到模块实现本身，即 `related_modules` 已能定位实现责任范围。
* `system_design`、`solution` 仍然成立，不需要改 contract、模块职责或技术主干。

回流到 `DESIGN`：

* 问题无法通过单模块实现修补解决。
* `related_contracts` 非空，或根因体现为 contract、data flow、project structure 缺陷。
* 多个模块同时受影响，失败点位于模块交接边界。

回流到 `SOLUTION`：

* 当前问题已经超出 design 细化层，表现为方案主干不成立。
* 模块职责划分错误、模块承接关系缺失或关键技术主干不合理。
* 不先调整 `selected_stack` 或 `module_mapping`，design 与 implementation 无法稳定重做。

回流到 `REQUIREMENTS`：

* 失败已无法通过 solution / design / implementation 层单独修复。
* 根因直接指向 `spec` 中的需求目标、硬约束或验收口径不稳定。
* `acceptance_criteria` 不足、冲突或在 testing 阶段被重新定义。

判断原则：

* `related_contracts` 非空不自动等于回 `DESIGN`；如果 contract 定义成立，只是实现未遵守，仍应优先回 `IMPLEMENTATION`。
* 如果多个 issue 指向不同层级，应按能够解释主失败现象的最高优先根因决定主回流目标。
