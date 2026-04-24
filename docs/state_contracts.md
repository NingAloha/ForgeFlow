# State Contract Reference

这一节定义各阶段状态文件的字段语义与约束，供 `State Manager`、各 agent 和 orchestrator 共享。

所有阶段必须输出结构化数据，当前以 `state/*.json` 作为最小持久化契约，后续再由 `schemas/*.py` 收敛为正式 Schema。

## 后续扩展约束

未来如果要增强 agent 能力，优先扩展结构化状态，而不是依赖更多自由文本说明。

优先考虑纳入结构化契约的扩展对象包括：

* 面向用户的澄清问题与回答
* 跨阶段持续跟踪的任务对象
* 可复用的阻塞项与问题归因
* agent 按需读取的上下文请求结果

这些对象在正式落入 `state/` 之前，应先满足两个原则：

* 能被 orchestrator 或下游 agent 稳定消费
* 不与现有五个主阶段状态混淆职责

相关演进原则见 [agent_design_principles.md](./agent_design_principles.md)。

## Structured Question State

`state/question_state.json`

这是当前已经引入的第一类扩展状态，用于承接 agent 面向用户的结构化澄清。

它解决的问题是：

* 某阶段已经识别到信息缺口，但不能只靠自由文本追问
* orchestrator 需要知道当前是否应该暂停推进并等待用户回答
* TUI 需要知道应该展示什么问题、有哪些可选项、回答后如何回填

当前契约如下：

```json
{
  "status": "idle",
  "stage_name": "",
  "state_key": "",
  "blocking": false,
  "questions": [
    {
      "id": "",
      "title": "",
      "description": "",
      "response_type": "single_select",
      "options": [
        {
          "label": "",
          "value": "",
          "hint": ""
        }
      ],
      "allow_free_text": false,
      "answer": {
        "selected_values": [],
        "free_text": ""
      }
    }
  ],
  "created_by": "",
  "resolution_summary": ""
}
```

字段说明：

* `status`：当前提问状态，当前使用 `idle`、`awaiting_user`、`answered`、`resolved`。
* `stage_name`：发起提问的阶段，例如 `REQUIREMENTS` 或 `SOLUTION`。
* `state_key`：本次提问主要关联的状态文件，例如 `spec` 或 `solution`。
* `blocking`：该组问题是否阻塞当前阶段继续推进。
* `questions`：当前待回答的问题列表。
* `questions[].id`：问题稳定标识，用于回答回填和去重。
* `questions[].title`：问题标题，要求简短明确。
* `questions[].description`：对问题背景和影响的解释。
* `questions[].response_type`：回答类型，建议值包括 `single_select`、`multi_select`、`free_text`、`mixed`。
* `questions[].options`：可选项列表；当回答类型不是纯自由输入时，应尽量提供。
* `questions[].options[].label`：用户可读标签。
* `questions[].options[].value`：结构化写回值。
* `questions[].options[].hint`：该选项的简短解释。
* `questions[].allow_free_text`：是否允许在选项之外补充自由回答。
* `questions[].answer`：当前问题的回答结果；在等待回答时可以为空对象或空值。
* `questions[].answer.selected_values`：选择型回答的结果列表。
* `questions[].answer.free_text`：自由文本补充。
* `created_by`：发起提问的 agent 或控制层名称。
* `resolution_summary`：问题被消费、写回状态并恢复流程后的简短总结。

约束：

* `question_state.json` 不替代 `spec.json` 或 `solution.json`，它只承载“澄清过程中的中间状态”。
* 同一时刻应尽量只有一组活动问题，避免多个阶段同时争抢用户输入。
* `blocking = true` 且 `status = awaiting_user` 时，orchestrator 应优先停留在当前阶段或进入显式等待态，而不是继续前推。
* 问题应优先面向“缺什么信息才能决策”，而不是面向“让用户重写整份需求文档”。
* `awaiting_user` 表示问题已发出、正在等用户回答；`answered` 表示用户已回答，控制层应把执行权重新交回对应阶段 agent，由它消费答案并写回主状态。
* 同阶段 agent 成功消费 `answered` 状态且没有发出新的问题时，控制层可以把 `question_state` 自动清回 `idle`。
* 若某问题已经被回答并写回主状态，应及时把 `status` 推进到 `resolved` 或清空为 `idle`。
* `questions[].options[].value` 应服务于状态回填，不能只写展示文本。
* 如果问题本质上是实现阻塞或测试缺陷，不应滥用本状态，而应分别进入 `implementation_status.json` 或 `test_report.json`。

职责边界：

* `Requirements Engineer` 和 `Solution Engineer` 是最先应使用这类状态的阶段角色。
* orchestrator 负责识别“有活动问题时是否暂停流程”。
* TUI 负责把 `questions` 渲染成明确可回答的交互，而不是只打印文字。
* 用户回答被消费后，最终仍应写回主阶段状态，而不是长期停留在 `question_state.json`。

为什么先从这个扩展对象开始：

* 它直接连接用户交互和状态机暂停机制。
* 它能最早验证“结构化交互”这条路线是否成立。
* 它对后续 `tasks`、`context fetch` 等对象的设计有示范作用。

## Requirements State

`state/spec.json`

用于保存需求阶段产物，只回答“要做什么”“给谁做”“做到什么算完成”，不讨论实现细节。

```json
{
  "project_goal": "",
  "target_users": [],
  "functional_requirements": [],
  "non_functional_requirements": [],
  "constraints": [],
  "preferences": [],
  "acceptance_criteria": [],
  "open_questions": []
}
```

字段说明：

* `project_goal`：项目最终目标，用一句话或一小段话描述要解决的问题。
* `target_users`：目标用户或使用者群体。
* `functional_requirements`：功能性需求列表，即系统必须提供的能力。
* `non_functional_requirements`：非功能性要求，如性能、稳定性、可维护性、交互体验。
* `constraints`：明确约束，如技术限制、运行环境限制、时间限制、接口限制。
* `preferences`：偏好项，不是硬约束，但会影响方案选择。
* `acceptance_criteria`：验收标准，用来判断需求是否真正完成。
* `open_questions`：当前还未澄清的问题，后续可能阻塞方案或设计。

## Solution State

`state/solution.json`

用于保存方案阶段产物，回答“整体准备怎么做”，重点是技术选型、模块划分、风险和备选方案。

```json
{
  "selected_stack": {
    "frontend": "",
    "backend": "",
    "database": "",
    "agent_framework": "",
    "deployment": ""
  },
  "module_mapping": [],
  "risks": [],
  "alternatives": []
}
```

字段说明：

* `selected_stack`：当前选定的技术栈。
* `selected_stack.frontend`：前端技术或界面层实现方案。
* `selected_stack.backend`：后端或核心执行层技术。
* `selected_stack.database`：状态存储、数据持久化或数据库方案。
* `selected_stack.agent_framework`：Agent 编排或模型调用框架。
* `selected_stack.deployment`：运行与部署方式。
* `module_mapping`：方案层的模块划分与职责映射，重点是“哪些需求由哪些模块承接”，不是字段级实现细节。
* `module_mapping[].module`：模块名称，使用稳定、可复用的命名。
* `module_mapping[].responsibilities`：该模块承担的职责列表。
* `module_mapping[].covers_requirements`：该模块直接承接的需求或能力点。
* `module_mapping[].depends_on`：该模块依赖的其他模块，用于表达方案层协作关系。
* `module_mapping[].tech_note`：可选的模块级技术说明，用于记录客户或方案对该模块的特殊技术偏好。
* `risks`：当前方案的主要风险点。
* `alternatives`：被考虑过的备选方案及其取舍空间。

约束：

* `module_mapping` 只描述方案层模块，不写文件名、类名、接口参数等设计细节。
* 当还没有任何有效模块方案时，`module_mapping` 应为空数组，而不是放一个空壳占位对象。
* 每一项必须能回答“这个模块负责什么”和“它承接了哪些需求”。
* `depends_on` 只写内部模块依赖，不写第三方库依赖；第三方技术归入 `selected_stack`。
* `tech_note` 只写影响方案决策的模块级技术偏好，例如“该功能必须使用 SQLite”或“该模块优先采用本地文件存储”，不展开为实现细节。
* 如果某项内容已经细到 API、目录、数据结构，应下沉到 `system_design.json`。

## Design State

`state/system_design.json`

用于保存设计阶段产物，回答“系统具体怎么组织”，比 solution 更落地，开始进入结构、契约和数据流。

```json
{
  "project_structure": {
    "directories": [],
    "modules": []
  },
  "contracts": [],
  "data_flow": [],
  "mvp_plan": {
    "in_scope": [],
    "out_of_scope": [],
    "milestones": [],
    "first_deliverable": ""
  }
}
```

字段说明：

* `project_structure`：项目结构定义。
* `project_structure.directories`：目录级组织方式。
* `project_structure.modules`：模块级拆分结果，通常比 solution 里的 `module_mapping` 更具体。
* `contracts`：模块间契约定义，用于描述清晰的交接边界。
* `contracts[].name`：契约名称，建议使用稳定命名规则，例如 `<producer>_to_<consumer>_<artifact>`。
* `contracts[].contract_type`：契约类型，如 `state_handoff`、`command`、`event`、`document`。
* `contracts[].producer`：产出该契约内容的模块或角色。
* `contracts[].consumers`：消费该契约内容的模块或角色列表。
* `contracts[].input`：生产该契约所依赖的输入项列表。
* `contracts[].input[].name`：输入项名称。
* `contracts[].input[].description`：输入项摘要说明。
* `contracts[].input[].required`：该输入项是否必需。
* `contracts[].output`：该契约交付的输出项列表。
* `contracts[].output[].name`：输出项名称。
* `contracts[].output[].description`：输出项摘要说明。
* `contracts[].output[].required`：该输出项是否为契约必交项。
* `contracts[].constraints`：契约执行时必须满足的约束条件。
* `contracts[].acceptance_criteria`：判断该契约交付成功的验收标准。
* `contracts[].failure_handling`：契约校验失败、缺字段或不满足约束时的处理方式。
* `data_flow`：契约在系统中的执行顺序与流转路径，是对 `contracts` 的流程化视图。
* `data_flow[].step`：流程步骤编号，用于表达先后顺序。
* `data_flow[].contract_name`：引用对应的契约名称，应与 `contracts[].name` 匹配。
* `data_flow[].from`：该步的发送方或发起方，通常应与对应契约的 `producer` 对齐。
* `data_flow[].to`：该步的接收方列表，通常应与对应契约的 `consumers` 对齐。
* `data_flow[].trigger`：触发该流转的条件、动作或事件。
* `data_flow[].notes`：对该流转步骤的补充说明，如异步、阻塞点、重试方式。
* `mvp_plan`：最小可用版本的落地计划，用于约束第一阶段实现范围与交付节奏。
* `mvp_plan.in_scope`：MVP 明确要实现的能力或范围。
* `mvp_plan.out_of_scope`：当前版本明确不做的内容，用于防止范围膨胀。
* `mvp_plan.milestones`：按阶段划分的里程碑列表。
* `mvp_plan.milestones[].name`：里程碑名称。
* `mvp_plan.milestones[].goal`：该里程碑想达到的目标。
* `mvp_plan.milestones[].deliverables`：该里程碑的交付物列表。
* `mvp_plan.first_deliverable`：第一阶段最先交付的可运行成果或最小闭环。

约束：

* `contracts` 只描述模块间或阶段间的交接契约，不写模块内部实现。
* 当设计尚未产出任何有效契约或流程步骤时，`contracts`、`data_flow`、`milestones` 都应为空数组，而不是放占位条目。
* 每一项必须能回答“谁产出”“谁消费”“交付什么”“需要遵守什么约束”“失败后怎么处理”。
* `input` 和 `output` 使用对象数组，保持在字段级或对象级摘要，不展开成完整 schema 实现。
* `constraints` 和 `acceptance_criteria` 分开维护，前者描述限制，后者描述交付完成判定。
* `consumers` 用数组表示，兼容一对一和一对多交接。
* 如果内容已经细到类定义、函数签名、数据库表结构，应下沉到更具体的设计文档或后续 schema。
* `data_flow` 不重复定义输入输出结构，它只引用已有契约并描述流转顺序。
* `data_flow[].contract_name`、`from`、`to` 应与对应 `contracts` 条目保持一致，不应形成第二套命名。
* `data_flow` 关注“何时流转、按什么顺序流转”，不负责补充新的契约规则。
* `mvp_plan` 只定义 MVP 范围和分阶段交付，不替代任务拆解或实现日志。
* `in_scope` 和 `out_of_scope` 必须互斥，避免同一能力同时出现在两边。
* `milestones` 关注阶段目标和交付物，不写具体代码提交或文件级变更。
* `first_deliverable` 应能独立表达“第一个值得跑起来的最小闭环是什么”。

## Implementation State

`state/implementation_status.json`

用于保存实现阶段产物，回答“当前代码实现到哪一步了”，重点是实际产出、测试和阻塞项。

```json
{
  "module_name": "",
  "implementation_status": "not_started",
  "files_touched": [],
  "tests_added_or_updated": [],
  "contract_compliance": true,
  "known_limitations": [],
  "blockers": []
}
```

字段说明：

* `module_name`：当前实现对象，通常是一个模块、子系统或本轮任务名。
* `implementation_status`：当前实现状态，如 `not_started`、`in_progress`、`blocked`、`done`。
* `files_touched`：本轮新增或修改过的文件列表。
* `tests_added_or_updated`：本轮新增或调整过的测试文件、测试用例或测试项。
* `contract_compliance`：实现是否符合上游 design 定义的契约。
* `known_limitations`：已经知道但暂未解决的限制。
* `blockers`：阻塞继续实现的问题。

约束：

* `implementation_status` 只描述当前实现进度，不替代设计文档或测试报告。
* `blocked` 表示当前仍处于实现阶段，但因为依赖缺失、设计问题、环境问题或未决条件而无法继续推进。
* `files_touched` 记录实际发生改动的文件，不要求区分新增和修改。
* `tests_added_or_updated` 记录本轮实现直接涉及的测试，不承担完整测试结论；完整验证结果应进入 `test_report.json`。
* `contract_compliance` 用于快速标记实现是否与 `system_design.json` 中的契约保持一致。
* `known_limitations` 和 `blockers` 分开维护，前者是已知缺陷或暂留问题，后者是阻塞继续推进的障碍。
* 编码或本地运行阶段发现的问题，优先记录在 `blockers`，由 `Implementation Engineer` 处理。

## Testing State

`state/test_report.json`

用于保存测试与验证阶段产物，回答“验证做了什么，结果怎么样，还有哪些问题”。

```json
{
  "test_scope": "integration",
  "result": "not_run",
  "issues": []
}
```

字段说明：

* `test_scope`：测试范围，如 `unit`、`integration`、`e2e`。
* `result`：测试结果，如 `pass`、`fail`、`partial`、`not_run`。
* `issues`：测试中发现的问题列表。
* `issues[].title`：问题标题，简要描述失败点或异常现象。
* `issues[].severity`：问题严重程度，如 `low`、`medium`、`high`、`critical`。
* `issues[].status`：问题当前状态，如 `open`、`confirmed`、`fixed`、`wont_fix`。
* `issues[].related_modules`：关联模块列表，用于表达单模块问题或多模块协作问题的责任范围。
* `issues[].related_contracts`：关联契约列表，用于表达问题与哪些模块交接边界或 contract 定义有关。
* `issues[].notes`：补充说明，如复现条件、影响范围、临时绕过方式。

约束：

* `test_report.json` 只记录验证结果与发现的问题，不记录实现过程本身。
* `result` 表示当前测试结论汇总，不替代单条 issue 的状态。
* `issues` 中每一项都应能独立表达一个可追踪问题，避免把多个问题混在一条里。
* 当当前轮验证尚未发现问题时，`issues` 应为空数组，而不是保留空壳问题对象。
* `related_modules` 应优先引用 `solution.json` 或 `system_design.json` 中已存在的模块名，避免新造命名。
* `related_contracts` 应优先引用 `system_design.json` 中已定义的 contract 名称，避免与 design 层脱节。
* 如果问题涉及模块交互、契约不一致或数据流断裂，应同时记录多个相关模块，而不是强行归因到单一模块。
* 如果问题直接体现为输入输出不匹配、契约约束冲突或交接失败，应同时记录相关 contract。
* 如果没有发现问题，`issues` 可以为空，但 `result` 仍应明确标记测试结论。
* 测试执行后产生的失败、异常和归因信息，统一进入 `issues`，由 `Test & Validation Engineer` 负责整理。

这些状态目前的特点是：

* 足够轻量，适合开发初期快速推进
* 以阶段输出为中心，而不是一次性塞进单个大对象
* 空数组明确表示“当前无有效条目”，不使用占位对象伪装已有产物
* 便于后续替换为 Pydantic 模型或增加版本字段
