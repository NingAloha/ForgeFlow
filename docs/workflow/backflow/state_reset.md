# Backflow State Reset

回流不仅是阶段切换，也意味着已有状态文件的有效性需要重新判断。

回流到 `IMPLEMENTATION`：

* `spec.json`、`solution.json` 与 `system_design.json` 仍可继续作为当前上游依据，前提是本次回流没有同时判定这些上游前提失效。
* `implementation_status.json` 继续作为当前活动状态文件，但其中的 `module_name`、`blockers`、`known_limitations` 与 `contract_compliance` 应根据当前修复目标重新整理。
* `test_report.json` 不能再直接视为当前有效结论。

回流到 `DESIGN`：

* `spec.json` 与 `solution.json` 仍可继续作为当前上游依据，前提是 requirements / solution 没有同时失效。
* `system_design.json` 不应再被默认视为当前有效 design 结论。
* `implementation_status.json` 与 `test_report.json` 只能作为历史参考。

回流到 `SOLUTION`：

* `spec.json` 仍可继续作为当前上游依据，前提是 requirements 没有同时失效。
* `solution.json` 不应再被默认视为当前有效方案结论。
* `system_design.json`、`implementation_status.json` 与 `test_report.json` 都应视为待重审。

回流到 `REQUIREMENTS`：

* `spec.json` 自身进入重新澄清与收敛阶段，旧内容可保留参考，但不能继续直接作为当前稳定需求前提。
* 所有下游状态都应视为待更新。

通用原则：

* 回流到某一上游阶段后，该阶段以下的下游状态文件都不应自动继承“当前有效”结论。
* 下游状态是否仍可复用，取决于其依赖前提是否仍成立，而不是文件内容是否仍然存在。
