# Workflow Stage Criteria

这一节定义单线程主流程中的正向阶段判定条件，主要供 `Project Orchestrator` 使用。

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

## `REQUIREMENTS_READY` 判定条件

在当前单线程主流程中，`REQUIREMENTS_READY` 表示需求已经足够清晰，可以进入 `solution` 阶段；它不要求需求绝对完整，但要求核心目标、主要能力和验收方向已经明确。

必须满足：

* `project_goal` 非空，且能清楚表达项目要解决的问题。
* `functional_requirements` 非空，且已经覆盖本轮要实现的主要能力。
* `acceptance_criteria` 非空，且至少能表达最关键的完成标准。

条件满足：

* `target_users` 建议明确；如果是显然的自用项目或内部工具，可以允许极简描述。
* `constraints` 如果用户已明确提出，则必须记录；如果当前没有识别到硬约束，可以为空。
* `non_functional_requirements` 与 `preferences` 可以为空，但只要用户明确提过相关内容，就应被记录。

不能推进到 `REQUIREMENTS_READY` 的情况：

* `open_questions` 中仍存在会阻塞方案设计的关键未决问题。
* 用户输入仍然停留在模糊意图层，无法稳定提炼出主要功能需求。
* 验收标准过于空泛，导致后续无法判断“做到什么算完成”。
* 用户已经给出硬约束，但 `constraints` 尚未记录，或与现有需求描述冲突。

orchestrator 的基础判断原则：

* 不以“字段是否全部填满”为 ready 标准，而以“是否已经足够进入方案设计”为准。
* 明确的新需求应直接进入正式需求字段；只有尚未澄清、会阻塞后续的问题才进入 `open_questions`。
* 如果需求内容已基本明确，但仍有非阻塞性小问题，可以先进入 `REQUIREMENTS_READY`，并在后续阶段继续补全。

## `SOLUTION_READY` 判定条件

在当前单线程主流程中，`SOLUTION_READY` 表示方案已经足够稳定，可以进入 `design` 阶段；它不要求所有技术细节都已经定死，但要求关键技术决策和核心模块划分已经明确。

必须满足：

* `selected_stack` 中与当前项目直接相关的关键技术位已经明确，尤其是核心执行层 `backend`。
* 如果项目存在明确交互层，则对应的 `frontend` 已明确；如果项目以 agent 为核心，则 `agent_framework` 已明确。
* `module_mapping` 非空，且已经列出本轮方案中的核心模块。
* 每个核心模块都具备基本职责说明，即 `module` 与 `responsibilities` 已形成稳定映射。
* 核心需求已经被模块承接，即主要 `functional_requirements` 在 `covers_requirements` 中已有归属。

条件满足：

* `database` 与 `deployment` 不要求一开始就非常细，但应至少有清晰方向，且不能与当前约束冲突。
* `depends_on` 建议明确主要模块依赖关系；如果当前只是粗粒度方案，可以允许后续在 design 阶段继续细化。
* `risks` 建议记录；如果当前存在明显风险但没有记入，会降低方案可用性。
* `alternatives` 可选，用于记录备选方案与取舍，不阻塞进入 `SOLUTION_READY`。
* `tech_note` 仅在存在模块级特殊技术偏好时填写，不影响 ready 判定。

不能推进到 `SOLUTION_READY` 的情况：

* 核心技术方案仍然悬空，导致 design 阶段无法继续展开结构设计。
* 关键需求尚未被任何模块承接，或多个模块职责明显重叠、边界混乱。
* 方案与 `spec` 中的硬约束冲突，或尚未体现用户已明确提出的技术限制。
* 方案只停留在技术名词罗列，尚未形成“技术选择 + 模块承接关系”的可设计结构。

orchestrator 的基础判断原则：

* 不以 `selected_stack` 每个字段都非空为 ready 标准，而以“关键技术位是否足够支撑 design”为准。
* 不以 `module_mapping` 条目数量为 ready 标准，而以“核心需求是否已有稳定模块承接”为准。
* 可以对所有 `module_mapping[].covers_requirements` 取并集作为覆盖集合，用于检查核心需求是否已被承接。
* 覆盖判断不要求与 `functional_requirements` 机械全等，而要求核心需求至少已被一个模块覆盖。
* `risks` 和 `alternatives` 用于提高方案质量，但不应取代核心方案判断。
* 如果方案主干已经明确，但仍有少量非阻塞性风险或备选项未补全，可以先进入 `SOLUTION_READY`，再在 design 阶段继续收紧。

## `DESIGN_READY` 判定条件

在当前单线程主流程中，`DESIGN_READY` 表示系统设计已经足够具体，可以进入 `implementation` 阶段；它不要求所有实现细节都已经定稿，但要求项目结构、关键交接边界、主流程流转和 MVP 范围已经能够指导编码落地。

必须满足：

* `project_structure.modules` 非空，且 solution 中的核心模块已经在 design 中有对应落位。
* `contracts` 已定义所有影响 MVP 主流程的关键交接边界。
* 每个关键 contract 都已经明确 `name`、`producer`、`consumers`、`input` 与 `output`。
* `data_flow` 非空，且已经串起 MVP 主流程中的关键步骤。
* `data_flow` 中出现的 `contract_name` 都能在 `contracts` 中找到对应条目。
* `mvp_plan.in_scope` 非空，且 `first_deliverable` 已明确，能够作为 implementation 的起点。

条件满足：

* `project_structure.directories` 建议明确主目录组织，但不要求穷尽所有子目录。
* `contracts[].contract_type` 与 `acceptance_criteria` 最好明确；`constraints` 和 `failure_handling` 建议有，但允许在后续阶段继续补细。
* `data_flow.trigger` 建议明确关键触发条件；`notes` 可作为补充说明，不影响 ready 判定。
* `mvp_plan.out_of_scope` 与 `milestones` 最好明确，用于防止范围膨胀，但不要求计划颗粒度过细。

不能推进到 `DESIGN_READY` 的情况：

* solution 中的核心模块在 design 中尚未落到可实现结构，导致 implementation 无法确定代码边界。
* 关键模块之间的交接边界仍然模糊，`contracts` 无法指导实现。
* `data_flow` 与 `contracts` 不一致，例如引用不存在的 contract，或 `from/to` 与对应契约明显冲突。
* MVP 范围尚未收住，implementation 阶段无法判断先做什么、暂时不做什么。
* 设计仍停留在结构草图层，尚不足以支持开发者开始编码。

orchestrator 的基础判断原则：

* 不以目录、contract 或 flow 的数量为 ready 标准，而以“是否已经能指导 implementation 开始工作”为准。
* `project_structure` 要验证 solution 的核心模块是否都已落到设计层，而不是仅列出目录名。
* `contracts` 只要求覆盖 MVP 主流程关键交接，不要求一次定义全部次要边界。
* `data_flow` 只要能串起主路径即可；异常分支、回流分支可以后续补全。
* `mvp_plan` 的目标是收范围、定起点，而不是替代详细开发计划。

## `IMPLEMENTING` 判定条件

在当前单线程主流程中，`IMPLEMENTING` 表示主流程已经正式进入按设计落地实现的阶段；它不是通过“写了多少代码”来定义，而是通过“orchestrator 是否已经切换到实现执行，并且实现动作已经开始”来定义。

进入 `IMPLEMENTING` 的条件：

* `DESIGN_READY` 已成立。
* 当前选定角色已切换为 `Implementation Engineer`。
* `implementation_status.json` 中的 `module_name` 已明确，表示当前存在具体实现对象。
* `implementation_status` 已进入活动状态，而非 `not_started`。

阶段语义：

* `in_progress` 表示当前正在按 design 落地实现。
* `blocked` 表示当前仍属于实现阶段，但因为阻塞条件尚未解除而无法继续推进。
* `done` 表示当前这轮实现已经完成，主流程可以准备进入 testing 判定。

不能视为已进入 `IMPLEMENTING` 的情况：

* design 尚未 ready，但已经试图直接开始编码。
* 当前没有明确实现对象，无法判断这一轮在落哪个模块或交付项。
* 仍停留在 `not_started`，说明实现动作尚未真正开始。

orchestrator 的基础判断原则：

* 是否进入 `IMPLEMENTING` 由“实现动作是否正式开始”决定，不由 `files_touched` 数量决定。
* `in_progress` 与 `blocked` 都属于实现中的活动状态。
* `done` 只表示实现阶段当前轮次完成，不自动等于整个流程结束。

## `TESTING` 判定条件

在当前单线程主流程中，`TESTING` 表示主流程已经从实现转入验证阶段；它的目标是确认当前实现结果是否满足 design 与需求预期，并对单模块问题、多模块协作问题以及 contract / data flow 问题进行归类与归因。

进入 `TESTING` 的条件：

* 当前这一轮实现已完成，即 `implementation_status` 已到达 `done`。
* 当前不存在会阻塞验证开始的实现级 `blockers`。
* 已有可验证对象，例如本轮实现涉及的模块、模块协作关系、关键 contracts、主流程 data flow、功能闭环或测试项已经明确。
* orchestrator 已将当前主角色切换为 `Test & Validation Engineer`。

阶段语义：

* `test_report.json` 成为当前验证阶段的主状态载体。
* `result = not_run` 表示已经进入 testing 阶段，但验证尚未真正执行完毕。
* `issues` 用于记录测试失败、异常现象以及模块级、契约级或数据流级归因结果。

不能视为已进入 `TESTING` 的情况：

* 实现仍处于 `not_started`、`in_progress` 或 `blocked`，尚未完成当前轮实现。
* 当前仍存在明显实现阻塞，导致测试无法开始。
* 尚未明确本轮要验证的对象、协作边界、关键 contract 或验证范围，导致 testing 只是空转。

orchestrator 的基础判断原则：

* 进入 `TESTING` 的前提是“当前轮实现已经可被验证”，而不是“测试文件已经存在”。
* `IMPLEMENTING` 的完成与 `TESTING` 的开始是相邻关系：实现完成后，主流程应转入验证，而不是直接视为完成。
* testing 阶段的核心任务不是继续实现，而是验证结果、检查模块交互、contract 与 data flow 是否成立、记录问题并决定是否回流。

## `DONE` 判定条件

在当前单线程主流程中，`DONE` 表示当前这一轮需求闭环已经完成：需求已被实现、经过验证，并且当前没有必须继续回流处理的阻塞问题。它表示“这一轮主流程完成”，不表示项目永久结束。

进入 `DONE` 的条件：

* 当前主流程已经完成 `TESTING`。
* `test_report.json` 中的 `result` 已有明确结论，且结果满足当前交付要求。
* 不存在会阻止交付的开放问题，尤其是高优先级或阻塞性的 `issues`。
* orchestrator 判断当前无需继续回流到 requirements、solution、design 或 implementation。

阶段语义：

* 当前轮需求的最小闭环已经完成。
* 当前结果已满足本轮 `acceptance_criteria` 与 MVP 交付目标。
* 后续如果出现新需求或新增变更，应视为开启下一轮流程，而不是继续停留在 `DONE` 内部处理。

不能视为已进入 `DONE` 的情况：

* `test_report.result` 仍为 `not_run`、`fail` 或其他不能支持交付的状态。
* 测试中仍存在需要继续修复的关键问题。
* 虽然测试结束，但 orchestrator 已判断必须回流到上游阶段处理设计、实现或需求问题。

orchestrator 的基础判断原则：

* `DONE` 不是“没有任何 issue”，而是“没有阻止当前轮交付的未决问题”。
* 是否进入 `DONE` 由“当前轮闭环是否完成”决定，而不是由开发活动是否暂时停止决定。
* 一旦用户提出新的明确需求，应开启下一轮流程，而不是把新需求并入当前 `DONE` 状态。
