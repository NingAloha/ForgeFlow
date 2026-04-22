# Workflow Backflow Rules

这一节定义单线程主流程中的回流规则，主要供 `Project Orchestrator` 在阶段失败、验证不通过或上游前提失效时使用。

## 回流总原则

回流不是异常补丁，而是主流程的一部分。它的目标不是“尽量少退”，而是把问题送回能够真正修正根因的阶段。

在当前单线程主流程中，是否回流以及回流到哪一层，应遵循以下原则：

* 回流按问题根因决定，不按当前卡住的位置决定。
* 优先回到能够修正根因的最低上游阶段，避免无意义地一路退回 `requirements`。
* 如果问题只影响当前阶段的执行结果，而不影响上游前提，则不应跨层回流。
* 如果下游阶段发现上游状态已经失效、冲突或不足以继续支撑当前工作，则必须回流。
* 回流判断以结构化状态为依据，重点参考 `implementation_status.json`、`test_report.json` 以及当前 design / solution / spec 是否仍然成立。
* 同一个问题如果同时表现为实现错误和设计缺陷，应优先按更上游的根因处理，避免在 implementation 层反复打补丁。
* 非阻塞性小问题不必立即触发回流；只有会影响当前阶段继续推进、验证结论或交付闭环的问题，才应触发正式回流。

orchestrator 的基础判断原则：

* 不以“出现 issue”本身作为回流条件，而以“当前问题是否说明当前阶段无法独立完成修复”作为判断标准。
* 回流后应重新以前一阶段的 ready 条件进行判定，而不是默认可以直接再次向前推进。
* 回流是阶段切换，不是状态覆盖；应保留问题归因信息，供后续重新推进时参考。

## 回流规则总表

| 当前阶段 | 主判断输入 | 留在当前阶段 | 回流目标 | 主要触发信号 |
| --- | --- | --- | --- | --- |
| `TESTING` | `test_report.json` | `result = not_run`，或 `partial` 但归因不足 | `IMPLEMENTING` | 问题主要是模块实现错误，`related_modules` 可定位，contract 本身仍成立 |
| `TESTING` | `test_report.json` + `system_design.json` | 不适用 | `DESIGN_READY` | `related_contracts` 指向 contract / data flow 缺陷，多模块边界失败 |
| `TESTING` | `test_report.json` + `solution.json` | 不适用 | `SOLUTION_READY` | 模块职责、承接关系或关键技术主干不成立 |
| `TESTING` | `test_report.json` + `spec.json` | 不适用 | `REQUIREMENTS_READY` | 验收口径、硬约束或需求目标本身不稳定 |
| `IMPLEMENTING` | `implementation_status.json` | `in_progress`，或 `blocked` 但只是环境 / 工具 / 依赖阻塞 | `DESIGN_READY` | contract、data flow、project structure 不足以指导当前实现 |
| `IMPLEMENTING` | `implementation_status.json` + `solution.json` | 不适用 | `SOLUTION_READY` | 模块职责、核心承接关系或技术路线错误 |
| `IMPLEMENTING` | `implementation_status.json` + `spec.json` | 不适用 | `REQUIREMENTS_READY` | 需求目标、约束或验收标准不足以支撑继续编码 |
| `DESIGN_READY` | `system_design.json` | design 仍可补完，未出现上游失效 | `SOLUTION_READY` | solution 无法落成稳定的结构、contract 或 flow |
| `DESIGN_READY` | `system_design.json` + `spec.json` | 不适用 | `REQUIREMENTS_READY` | 需求目标、范围、验收口径或约束不稳，导致 design 无法收敛 |
| `SOLUTION_READY` | `solution.json` + `spec.json` | 方案仍可收紧，主干未失效 | `REQUIREMENTS_READY` | 需求目标、约束、验收标准或 MVP 范围不稳，导致方案无法收敛 |

## `TESTING -> IMPLEMENTING / DESIGN / SOLUTION / REQUIREMENTS`

在当前单线程主流程中，`TESTING` 阶段的核心任务是验证当前实现是否满足 `spec`、`solution` 与 `design`。如果验证未通过，orchestrator 应优先读取 `state/test_report.json` 中的 `result` 与 `issues`，再结合 `state/implementation_status.json`、`state/system_design.json`、`state/solution.json` 与 `state/spec.json` 判断根因属于哪一层。

应维持在 `TESTING`，而不是立即回流的情况：

* `test_report.result = not_run`，说明当前只是尚未执行完验证，不构成回流依据。
* `test_report.result = partial`，但现有 `issues` 仍不足以判断根因层级，orchestrator 应先补齐验证或归因信息。
* 当前问题只是测试执行不完整、测试环境暂未就绪或验证范围未收齐，尚不能说明 implementation / design / solution / requirements 出现失效。

应回流到 `IMPLEMENTING` 的情况：

必须同时满足：

* `test_report.result` 为 `fail` 或 `partial`，且当前结论不足以进入 `DONE`。
* `test_report.issues` 中至少存在一项 `status` 为 `open` 或 `confirmed` 的问题。
* 问题可主要归因到模块实现本身，即 `issues[].related_modules` 已能定位实现责任范围。

同时通常表现为：

* `issues[].related_contracts` 为空，或虽有关联 contract，但问题本质仍是消费方 / 生产方实现不符合既有 contract。
* `system_design.json.contracts`、`data_flow` 与 `solution.json.module_mapping` 仍然能够自洽，不需要改 contract、模块职责或技术主干。
* `implementation_status.json.contract_compliance = false`，或虽为 `true` 但测试表明实际行为与 design 交付要求不符。
* 修复动作主要会落在 `files_touched` 对应实现代码、测试补充或局部容错逻辑，而不是回写上游文档。

典型信号：

* 单模块功能错误。
* 边界条件遗漏。
* 输出值不符合既有 contract 约束，但 contract 定义本身没有问题。
* 测试发现已实现逻辑与 `acceptance_criteria` 的落地行为不一致，但并不需要重定义需求口径。

应回流到 `DESIGN_READY` 的情况：

必须同时满足：

* `test_report.result` 为 `fail` 或 `partial`。
* `test_report.issues` 中的问题无法通过单模块实现修补解决。
* 问题已经体现为 `system_design.json` 中 contract、data flow 或 project structure 的缺陷。

同时通常表现为：

* `issues[].related_contracts` 非空，且问题直接指向输入输出定义不足、contract 约束冲突、failure handling 缺失或 `data_flow` 无法闭环。
* 多个 `related_modules` 同时受影响，说明失败点位于模块交接边界，而不是某一模块内部逻辑。
* 现有 `contracts[].input`、`contracts[].output`、`constraints` 或 `acceptance_criteria` 不足以指导实现者修复问题。
* 按当前 design 即使继续修改代码，也会在相同交接边界上重复失败。

典型信号：

* 生产方和消费方都“按各自理解”实现，但 contract 没有把边界说清。
* `data_flow[].contract_name` 能找到对应 contract，但触发条件、发送方 / 接收方关系无法支撑主流程。
* 某个 MVP 主路径在设计层没有定义失败处理，导致测试只能确认流程断裂，不能指导实现修复。

应回流到 `SOLUTION_READY` 的情况：

必须同时满足：

* `test_report.result` 为 `fail` 或 `partial`。
* 当前问题已经超出 design 细化层，表现为方案主干不成立。
* 不先调整 `solution.json.selected_stack` 或 `module_mapping`，design 与 implementation 无法稳定重做。

同时通常表现为：

* `issues[].related_modules` 指向多个核心模块，且根因是职责划分错误、模块承接关系缺失或关键依赖关系不合理。
* `solution.json.module_mapping[].covers_requirements` 无法稳定覆盖测试中失败的核心需求。
* 当前选定技术路线与 `spec.json.constraints` 或非功能要求冲突，导致设计和实现即使修补也无法满足交付目标。
* 问题不只是 contract 怎么写，而是“该能力本来就不该由这些模块这样承接”。

典型信号：

* 某核心需求在测试时发现没有任何稳定模块负责到底。
* 两个模块长期相互推诿同一职责，说明 `module_mapping` 边界错误。
* 关键技术位选型使主能力无法达到预期，已经不是 design 补字段能解决的问题。

应回流到 `REQUIREMENTS_READY` 的情况：

必须同时满足：

* `test_report.result` 为 `fail` 或 `partial`，且失败已无法通过 solution / design / implementation 层单独修复。
* 根因直接指向 `spec.json` 中的需求目标、硬约束或验收口径不稳定。

同时通常表现为：

* `spec.json.acceptance_criteria` 无法支持当前测试结论判定，或不同标准之间互相冲突。
* `spec.json.constraints` 与现有方案 / 实现方向冲突，而该冲突在上游没有被澄清。
* `spec.json.open_questions` 中原本遗留的问题在测试阶段被证明是阻塞性交付问题。
* 用户在 testing 阶段新增或改写关键目标、硬约束或完成标准，导致既有 `solution` 与 `design` 整体失效。

典型信号：

* 测试通过某一实现路径，但团队仍无法判断是否算“完成”。
* 用户接受标准在验证时被重新定义。
* 原始需求遗漏了关键约束，导致此前所有下游决策建立在错误前提上。

orchestrator 的基础判断原则：

* 优先以 `test_report.json` 为主判断输入，尤其关注 `result`、`issues[].severity`、`issues[].status`、`related_modules` 与 `related_contracts`。
* `related_contracts` 非空不自动等于回 `DESIGN_READY`；如果 contract 定义本身成立，只是实现未遵守，仍应优先回 `IMPLEMENTING`。
* 只有当 `issues` 已经说明 `system_design`、`solution` 或 `spec` 本身失效时，才应回到更上游阶段。
* 如果多个 issue 指向不同层级，应按能够解释主失败现象的最高优先根因决定主回流目标，并将其余问题保留在 `issues` 中继续跟踪。

## `IMPLEMENTING -> DESIGN / SOLUTION / REQUIREMENTS`

在当前单线程主流程中，`IMPLEMENTING` 阶段的主判断输入是 `state/implementation_status.json`。orchestrator 应优先读取其中的 `module_name`、`implementation_status`、`contract_compliance`、`known_limitations` 与 `blockers`，再结合 `state/system_design.json`、`state/solution.json` 与 `state/spec.json` 判断当前阻塞是否仍可在实现层解决。

应维持在 `IMPLEMENTING`，而不是立即回流的情况：

* `implementation_status` 为 `in_progress`，且当前没有上游前提失效信号。
* `implementation_status` 为 `blocked`，但 `blockers` 主要是执行性问题，例如本地环境、依赖、工具链、权限、临时资源缺失。
* `contract_compliance = false`，但根因明确是当前实现尚未补完，而 `system_design.json.contracts` 本身足够清晰。
* 当前限制只属于 `known_limitations`，尚未阻止本轮实现继续推进，也未说明 design / solution / requirements 失效。

应回流到 `DESIGN_READY` 的情况：

必须同时满足：

* `implementation_status` 为 `blocked`，或虽为 `in_progress` 但当前实现已无法在既有设计前提下继续稳定推进。
* `blockers` 或已知问题直接指向 `system_design.json` 中 contract、data_flow 或 project_structure 的缺口。
* 当前问题不能仅通过补代码解决，必须先补充或修正 design。

同时通常表现为：

* `contract_compliance = false`，且不是因为代码没写完，而是因为 `contracts[].input`、`output`、`constraints` 或 `failure_handling` 本身不足以指导实现。
* `project_structure.modules` 与当前 `module_name` 的边界关系不清，导致开发者无法判断代码应落在哪一层或如何与其他模块协作。
* `data_flow` 没有定义实现当前模块所需的关键触发路径、发送方 / 接收方或主流程顺序。
* 当前阻塞可以明确表述为“设计没把交接边界说清楚”。

典型信号：

* 开发者无法确定某个输入字段该由谁提供。
* 消费方需要的数据在 contract 中没有定义。
* 两个模块的协作顺序在 data flow 中没有被明确，导致实现无法继续。

应回流到 `SOLUTION_READY` 的情况：

必须同时满足：

* `implementation_status` 为 `blocked`，或当前实现即使继续写代码也只会放大结构性问题。
* 根因已经超出 design 细化层，表现为方案层模块承接关系、职责划分或关键技术主干不成立。
* 不先调整 `solution.json.module_mapping` 或 `selected_stack`，design 与 implementation 都无法稳定继续。

同时通常表现为：

* 当前 `module_name` 对应职责与 `solution.json.module_mapping` 的描述冲突，或多个模块同时覆盖同一核心需求却没有清晰分工。
* 某核心需求在实现阶段发现没有稳定承接模块，导致开发者无法确定应该在哪个模块完成该能力。
* 当前技术路线与需求约束冲突，开发阶段已经确认不是补一个 contract 或重画 data flow 能解决的问题。
* 当前阻塞可以明确表述为“方案主干不成立，而不是设计没写细”。

典型信号：

* 一个能力既像后端职责又像 agent 职责，但 solution 没定谁负责到底。
* 为满足一个核心需求，当前必须跨多个模块绕行实现，说明方案层承接关系有问题。
* 实现阶段确认既定技术选型无法满足关键能力或约束。

应回流到 `REQUIREMENTS_READY` 的情况：

必须同时满足：

* `implementation_status` 为 `blocked`，或继续实现会直接建立在错误需求前提上。
* 根因直接指向 `spec.json` 中需求目标、约束或验收标准不稳定。

同时通常表现为：

* `spec.json.acceptance_criteria` 缺失或过于空泛，导致开发者无法判断实现完成标准。
* `spec.json.constraints` 与当前实现方向冲突，而该冲突不是 solution 选型失误，而是需求层尚未澄清。
* `spec.json.open_questions` 中存在阻塞当前实现的关键未决问题。
* 用户在实现阶段新增关键目标、约束或优先级，导致已有 solution / design 无法继续作为当前实现依据。

典型信号：

* 开发者无法判断某行为是 bug 还是符合预期，因为验收标准没有定义。
* 实现做到一半才发现需求对运行环境或能力边界另有硬限制。
* 当前争议已经从“怎么实现”变成“到底要不要这样做”。

orchestrator 的基础判断原则：

* `implementation_status = blocked` 不自动等于回流；关键在于 `blockers` 是否说明上游前提失效。
* `contract_compliance = false` 也不自动等于回 `DESIGN_READY`；如果只是实现暂未满足既有 contract，仍应留在 `IMPLEMENTING`。
* 只有当 `blockers`、`known_limitations` 或上下游状态已经表明 design / solution / requirements 本身不足时，才应触发正式回流。
* 一旦确认当前问题无法在既有 design 前提下通过继续编码解决，应停止局部修补并正式回流到对应上游阶段。

## `DESIGN_READY -> SOLUTION_READY / REQUIREMENTS_READY`

在当前单线程主流程中，`DESIGN_READY` 阶段的主判断输入是 `state/system_design.json`。orchestrator 应优先读取其中的 `project_structure`、`contracts`、`data_flow` 与 `mvp_plan`，再结合 `state/solution.json` 与 `state/spec.json` 判断当前 design 是否只是未补完，还是已经暴露出上游前提不足。

应维持在 `DESIGN_READY`，而不是立即回流的情况：

* `project_structure.modules`、`contracts`、`data_flow` 或 `mvp_plan` 尚在细化，但核心主干已经能继续补充，不存在明确上游失效。
* 当前缺的是 design 细节，例如补充目录组织、增加非关键 contract、完善 `notes` 或 `failure_handling`，而不是重做方案或需求。
* `contracts` 尚未覆盖所有次要边界，但 MVP 主流程关键交接已经有稳定落点。
* 当前问题只说明 design 还不够完整，不说明 `solution.json` 或 `spec.json` 本身不成立。

应回流到 `SOLUTION_READY` 的情况：

必须同时满足：

* 当前 design 无法继续稳定展开，或虽能继续写文档，但无法形成可指导 implementation 的结构。
* 根因直接指向 `solution.json` 中技术主干、模块承接关系或职责划分不足。
* 不先调整 solution，`system_design.json` 无法补成 `DESIGN_READY` 所要求的可实现结构。

同时通常表现为：

* `project_structure.modules` 无法给 `solution.json.module_mapping` 中的核心模块找到稳定落位。
* `contracts` 难以定义，不是因为字段没想全，而是因为 producer / consumer 的模块边界在 solution 层就不稳定。
* `data_flow` 无法串起 MVP 主流程，不是因为步骤没写完，而是因为方案层没有明确哪些模块负责承接关键能力。
* `mvp_plan.in_scope` 中的核心能力无法映射回 `module_mapping[].covers_requirements`，说明方案承接关系本身不足。

典型信号：

* solution 中的某个核心模块在 design 里无法落成具体结构。
* 设计阶段发现两个模块职责长期重叠，contract 无法稳定命名和分配。
* 设计要继续推进，必须先改模块边界、依赖关系或关键技术方向。

应回流到 `REQUIREMENTS_READY` 的情况：

必须同时满足：

* 当前 design 无法继续收敛成可实现结构。
* 根因直接指向 `spec.json` 中需求目标、验收标准、约束或范围边界不稳定。

同时通常表现为：

* `contracts` 无法定义关键输入输出，不是因为设计能力不足，而是因为需求本身没有说清“交付什么算完成”。
* `mvp_plan.in_scope` 和 `first_deliverable` 无法确定，因为 `spec.json.acceptance_criteria` 不足以收敛 MVP。
* `spec.json.constraints` 缺失、冲突或在 design 阶段才暴露为关键阻塞，导致目录结构、模块边界或数据流都无法稳定设计。
* `spec.json.open_questions` 中仍存在会阻塞 contract 定义或主流程闭环的关键问题。

典型信号：

* 设计阶段无法判断主流程终点是什么，因为验收标准不明确。
* 不同设计方案都成立，但缺少需求层口径来决定哪一个才是正确方向。
* 用户在设计阶段调整核心目标、范围或约束，导致原有 solution 失去依据。

orchestrator 的基础判断原则：

* `contracts` 或 `data_flow` 为空，不自动等于回流；先判断是 design 尚未补完，还是上游前提不足。
* 如果问题体现为“方案不足以支撑 design”，回 `SOLUTION_READY`。
* 如果问题体现为“需求不足以支撑 solution 和 design”，回 `REQUIREMENTS_READY`。
* design 阶段不应代替 solution 或 requirements 偷偷重写上游决策；一旦确认根因在上游，应显式回流。

## `SOLUTION_READY -> REQUIREMENTS_READY`

在当前单线程主流程中，`SOLUTION_READY` 阶段的主判断输入是 `state/solution.json`。orchestrator 应优先读取其中的 `selected_stack`、`module_mapping`、`risks` 与 `alternatives`，再结合 `state/spec.json` 判断当前方案是尚未收紧，还是已经暴露出 requirements 前提不成立。

应维持在 `SOLUTION_READY`，而不是立即回流的情况：

* `selected_stack` 尚未完全补齐，但与当前项目直接相关的关键技术位已有清晰方向。
* `module_mapping` 还在细化，但核心需求已经有基本承接关系。
* `risks` 或 `alternatives` 仍在补充，但不影响当前形成稳定方案主干。
* 当前问题只是“方案还不够完整”，不说明 `spec.json` 中需求目标、约束或验收标准已经失效。

应回流到 `REQUIREMENTS_READY` 的情况：

必须同时满足：

* 当前方案无法稳定收敛成可进入 design 的主干。
* 根因直接指向 `spec.json` 中需求目标、验收标准、约束或范围边界不稳定。

同时通常表现为：

* `module_mapping` 无法稳定回答“哪些模块承接哪些需求”，因为 `spec.json.functional_requirements` 本身仍然模糊或不断变化。
* `selected_stack` 无法收敛，不是因为技术判断不足，而是因为 `constraints`、`preferences` 或目标场景尚未明确。
* `acceptance_criteria` 缺失、冲突或过于空泛，导致方案无法判断什么能力必须优先承接。
* `open_questions` 中仍存在会阻塞方案决策的关键问题，而这些问题已经不适合继续靠方案层假设推进。

典型信号：

* 不同方案都看似可行，但缺少需求层标准来决定哪条路线正确。
* 某个核心能力是否要做、做到什么程度、是否属于 MVP，都还没有被需求层确定。
* 用户新增硬约束或改写目标后，原有 `selected_stack` 与 `module_mapping` 失去依据。

orchestrator 的基础判断原则：

* `selected_stack` 某些字段为空，不自动等于回流；关键在于方案主干是否还能稳定承接需求。
* 如果方案无法稳定回答“哪些模块承接哪些需求”，优先检查 `spec.json` 是否已经达到 `REQUIREMENTS_READY` 的前提。
* solution 阶段不能通过主观假设替代关键需求澄清。
* 只有在需求前提稳定后，`SOLUTION_READY` 才有意义。

## 回流后的状态处理原则

在当前单线程主流程中，回流不仅是主状态切换，也意味着已有状态文件的有效性需要重新判断。orchestrator 在决定回流目标后，应同步判断哪些下游状态仍可复用，哪些只能保留为历史参考，不能继续作为当前有效结论。

回流到 `IMPLEMENTING` 后的处理标准：

* `spec.json`、`solution.json` 与 `system_design.json` 仍可继续作为当前上游依据，前提是本次回流没有同时判定这些上游前提失效。
* `implementation_status.json` 应继续作为当前活动状态文件，但其中的 `module_name`、`blockers`、`known_limitations` 与 `contract_compliance` 应根据当前修复目标重新整理。
* 已有 `test_report.json` 不能再直接视为当前有效结论；即使问题定位清楚，测试结果也只能作为待复验记录保留。

回流到 `DESIGN_READY` 后的处理标准：

* `spec.json` 与 `solution.json` 仍可继续作为当前上游依据，前提是本次回流没有同时判定 requirements / solution 失效。
* `system_design.json` 不应再被默认视为当前有效 design 结论，尤其是被判定有问题的 `contracts`、`data_flow`、`project_structure` 或 `mvp_plan` 部分。
* 现有 `implementation_status.json` 与 `test_report.json` 只能作为历史参考，因为它们建立在旧 design 前提上。

回流到 `SOLUTION_READY` 后的处理标准：

* `spec.json` 仍可继续作为当前上游依据，前提是本次回流没有同时判定 requirements 失效。
* `solution.json` 不应再被默认视为当前有效方案结论，尤其是被判定失效的 `selected_stack`、`module_mapping`、`risks` 或主干判断。
* `system_design.json`、`implementation_status.json` 与 `test_report.json` 都应视为待重审，因为它们依赖旧 solution 前提。

回流到 `REQUIREMENTS_READY` 后的处理标准：

* `spec.json` 自身进入重新澄清与收敛阶段，旧内容可保留参考，但不能继续直接作为当前稳定需求前提。
* `solution.json`、`system_design.json`、`implementation_status.json` 与 `test_report.json` 都应视为待更新。
* 只有当新的 requirements 再次满足 `REQUIREMENTS_READY` 判定条件后，下游阶段才应重新建立。

必须遵循：

* 回流到某一上游阶段后，该阶段以下的下游状态文件都不应自动继承“当前有效”结论。
* 下游状态是否仍可复用，取决于其依赖前提是否仍成立，而不是文件内容是否仍然存在。
* 如果回流根因影响的是阶段主干前提，则依赖该前提的所有下游判定都应失效。
* 如果回流只影响局部实现，则 requirements / solution / design 的 ready 结论通常可以保留，但 testing 结论需要重新获取。

建议处理：

* orchestrator 应保留原有状态内容作为历史参考，但应明确区分“历史记录”与“当前有效结论”。
* 回流后再次前进时，应重新检查对应阶段的 ready 条件，而不是按原路径直接跳回原下游阶段。
* `test_report.json.issues` 中已发现的问题应继续保留，直到被重新验证为 `fixed`、`wont_fix` 或明确不再适用。
* `implementation_status.json.blockers` 与 `known_limitations` 应在每次回流后重新整理，避免旧阻塞长期污染当前阶段判断。

orchestrator 的基础判断原则：

* 回流后的关键任务是恢复“上游前提重新成立”，而不是尽快回到原来的阶段名。
* 状态文件可以继续存在，但其“是否仍代表当前有效阶段结论”必须重新判定。
