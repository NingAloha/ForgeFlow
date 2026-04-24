# `DESIGN` Criteria

`DESIGN` 表示系统设计已经足够具体，可以进入 `IMPLEMENTATION` 阶段。

必须满足：

* `project_structure.modules` 非空，且 solution 中的核心模块已经在 design 中有对应落位。
* `contracts` 已定义所有影响 MVP 主流程的关键交接边界。
* 每个关键 contract 都已经明确 `name`、`producer`、`consumers`、`input` 与 `output`。
* `data_flow` 非空，且已经串起 MVP 主流程中的关键步骤。
* `data_flow` 中出现的 `contract_name` 都能在 `contracts` 中找到对应条目。
* `mvp_plan.in_scope` 非空，且 `first_deliverable` 已明确。

建议满足：

* `project_structure.directories` 尽量明确主目录组织，但不要求穷尽所有子目录。
* `contracts[].contract_type` 与 `acceptance_criteria` 最好明确；`constraints` 和 `failure_handling` 建议有，但允许后续继续补细。
* `data_flow.trigger` 建议明确关键触发条件；`notes` 可作为补充说明。
* `mvp_plan.out_of_scope` 与 `milestones` 最好明确，用于防止范围膨胀。

不能推进的情况：

* solution 中的核心模块在 design 中尚未落到可实现结构。
* 关键模块之间的交接边界仍然模糊，`contracts` 无法指导实现。
* `data_flow` 与 `contracts` 不一致。
* MVP 范围尚未收住，implementation 阶段无法判断先做什么。
* 设计仍停留在结构草图层，尚不足以支持开发者开始编码。

orchestrator 判断原则：

* 不以目录、contract 或 flow 的数量为 ready 标准，而以“是否已经能指导 implementation 开始工作”为准。
* `contracts` 只要求覆盖 MVP 主流程关键交接，不要求一次定义全部次要边界。
* `data_flow` 只要能串起主路径即可；异常分支、回流分支可以后续补全。
* `mvp_plan` 的目标是收范围、定起点，而不是替代详细开发计划。
