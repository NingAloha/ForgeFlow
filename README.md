# ForgeFlow / ForgeShell

## A Multi-Agent Software Engineering Pipeline with Chat TUI

---

## 1. Overview

**ForgeFlow** 是一个多 Agent 软件工程执行系统，用于将用户需求逐步转化为：

* 需求规格（Specification）
* 技术方案（Solution）
* 系统结构（Design）
* 代码实现（Implementation）
* 测试验证（Testing）

**ForgeShell** 是其终端交互界面（TUI），提供类似 Copilot CLI 的**聊天式体验**，但具备更强的工程流程控制能力。

---

## 2. Core Design Principles

* **Separation of Concerns**：每个 Agent 只负责一层职责
* **Contract-driven**：所有阶段通过结构化数据衔接
* **Implicit Orchestration**：默认自动调度
* **Explicit Control (Optional)**：用户可手动干预
* **State Transparency**：状态可见但不打扰

---

## 3. System Architecture

```text
User
  ↓
ForgeShell (Chat TUI)
  ↓
Project Orchestrator
  ├── State Manager
  ├── Requirements Engineer
  ├── Solution Engineer
  ├── System Designer
  ├── Implementation Engineer
  └── Test & Validation Engineer
```

---

## 4. Agent Roles

### 4.1 Requirements Engineer

将用户需求转化为结构化需求规格。

### 4.2 Solution Engineer

根据需求规格设计技术方案与技术选型。

### 4.3 System Designer

将技术方案转化为系统结构、接口契约与项目骨架。

### 4.4 Implementation Engineer

实现模块代码并负责单元测试。
当问题发生在当前编码或本地运行阶段时，优先由该角色分析原因并记录为实现阻塞。

### 4.5 Test & Validation Engineer

执行功能测试、集成测试并进行问题归因。
当系统已经进入验证阶段时，由该角色负责失败归类、影响判断和模块归因。

---

## 5. Control Layer

### 5.1 Project Orchestrator

负责系统流程层决策，是用户输入、当前状态与各层 agent 之间的统一调度入口。

职责：

* 根据用户输入与当前阶段，选择当前应执行的角色或动作。
* 控制流程推进、暂停、回流、重试和终止。
* 判断当前结果是否可以进入下一阶段，或必须回到上游层修正。
* 判断是否需要用户确认，或可以继续自动推进。
* 协调各 agent 的执行顺序，并决定何时调用 State Manager 读取或写入状态。
* 对外提供流程层解释，例如当前为何停留在某阶段、为何发生回流或等待。

输入：

* 用户当前输入或显式命令。
* 当前模式，如 `AUTO`、锁定角色、手动切换等控制状态。
* 当前阶段状态与各 state 文件摘要。
* 最近一次 agent 执行结果。
* 当前是否存在 `open_questions`、`blockers`、测试 `issues` 或其他阻塞信息。

输出：

* 当前选定的角色。
* 下一步动作，如继续执行、进入下一阶段、回流、重试、等待确认。
* 对 agent 或 State Manager 的调度请求。
* 面向用户的流程层说明。

不负责：

* 不直接维护具体业务文档内容，内容产出仍由各层 agent 负责。
* 不直接持久化 state 文件，状态读写由 State Manager 统一处理。
* 不替代具体 agent 执行需求分析、技术设计、编码或测试工作。
* 不负责底层存储格式、schema 校验或状态 diff 计算。

### 5.2 State Manager

负责系统状态的统一读写与一致性维护，是所有阶段状态文件的唯一持久化入口。

职责：

* 维护阶段状态文件（Spec / Solution / Design / Implementation / Test）。
* 接收各层 agent 产出的结构化内容，并统一持久化到对应 state 文件。
* 提供统一状态读取，屏蔽底层 JSON 文件路径与格式细节。
* 负责状态写入、覆盖、局部更新和阶段结果落盘。
* 负责基础校验，确保写入内容符合当前 state contract。
* 提供状态快照、版本比对或 diff 能力，供上层查看变化。
* 为 orchestrator 和各 agent 提供稳定的状态访问接口。

输入：

* 当前目标 state 类型，如 `spec`、`solution`、`design`、`implementation`、`test`。
* 上游 agent 产出的结构化结果。
* orchestrator 发起的读取、写入、更新、回滚或比较请求。

输出：

* 标准化后的 state 数据。
* 写入成功或失败结果。
* 校验错误信息。
* 当前状态变更说明或状态差异信息。

不负责：

* 不决定当前该执行哪个角色。
* 不决定是否推进、回流、重试或终止流程。
* 不分析用户语义，也不做任务规划。
* 不解释业务错误原因；错误归因仍由实现或验证角色负责。
* 不负责对 agent 工作结果做流程层总结；“这轮结果意味着什么、下一步怎么办”由 orchestrator 判断。
* 各层文档内容由对应 agent 负责，State Manager 只负责统一存储与一致性维护。

---

## 6. State Machine

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

### 6.1 `REQUIREMENTS_READY` 判定条件

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

### 6.2 `SOLUTION_READY` 判定条件

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

### 6.3 `DESIGN_READY` 判定条件

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

### 6.4 `IMPLEMENTING` 判定条件

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

### 6.5 `TESTING` 判定条件

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

### 6.6 `DONE` 判定条件

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

---

## 7. Data Contracts

所有阶段必须输出结构化数据，当前以 `state/*.json` 作为最小持久化契约，后续再由 `schemas/*.py` 收敛为正式 Schema。

### 7.1 Requirements State

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

### 7.2 Solution State

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
  "module_mapping": [
    {
      "module": "",
      "responsibilities": [],
      "covers_requirements": [],
      "depends_on": [],
      "tech_note": ""
    }
  ],
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
* 每一项必须能回答“这个模块负责什么”和“它承接了哪些需求”。
* `depends_on` 只写内部模块依赖，不写第三方库依赖；第三方技术归入 `selected_stack`。
* `tech_note` 只写影响方案决策的模块级技术偏好，例如“该功能必须使用 SQLite”或“该模块优先采用本地文件存储”，不展开为实现细节。
* 如果某项内容已经细到 API、目录、数据结构，应下沉到 `system_design.json`。

### 7.3 Design State

`state/system_design.json`

用于保存设计阶段产物，回答“系统具体怎么组织”，比 solution 更落地，开始进入结构、契约和数据流。

```json
{
  "project_structure": {
    "directories": [],
    "modules": []
  },
  "contracts": [
    {
      "name": "",
      "contract_type": "",
      "producer": "",
      "consumers": [],
      "input": [
        {
          "name": "",
          "description": "",
          "required": true
        }
      ],
      "output": [
        {
          "name": "",
          "description": "",
          "required": true
        }
      ],
      "constraints": [],
      "acceptance_criteria": [],
      "failure_handling": []
    }
  ],
  "data_flow": [
    {
      "step": 1,
      "contract_name": "",
      "from": "",
      "to": [],
      "trigger": "",
      "notes": ""
    }
  ],
  "mvp_plan": {
    "in_scope": [],
    "out_of_scope": [],
    "milestones": [
      {
        "name": "",
        "goal": "",
        "deliverables": []
      }
    ],
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

### 7.4 Implementation State

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

### 7.5 Testing State

`state/test_report.json`

用于保存测试与验证阶段产物，回答“验证做了什么，结果怎么样，还有哪些问题”。

```json
{
  "test_scope": "integration",
  "result": "not_run",
  "issues": [
    {
      "title": "",
      "severity": "",
      "status": "",
      "related_modules": [],
      "related_contracts": [],
      "notes": ""
    }
  ]
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
* `related_modules` 应优先引用 `solution.json` 或 `system_design.json` 中已存在的模块名，避免新造命名。
* `related_contracts` 应优先引用 `system_design.json` 中已定义的 contract 名称，避免与 design 层脱节。
* 如果问题涉及模块交互、契约不一致或数据流断裂，应同时记录多个相关模块，而不是强行归因到单一模块。
* 如果问题直接体现为输入输出不匹配、契约约束冲突或交接失败，应同时记录相关 contract。
* 如果没有发现问题，`issues` 可以为空，但 `result` 仍应明确标记测试结论。
* 测试执行后产生的失败、异常和归因信息，统一进入 `issues`，由 `Test & Validation Engineer` 负责整理。

这些状态目前的特点是：

* 足够轻量，适合开发初期快速推进
* 以阶段输出为中心，而不是一次性塞进单个大对象
* 便于后续替换为 Pydantic 模型或增加版本字段

---

## 8. ForgeShell (TUI)

### 8.1 Design Goal

提供一个：

* 聊天式交互
* 自动调度
* 状态可视化
* 可控但不复杂

的终端体验。

---

## 8.2 Layout（关键改动）

采用**上下对称布局（Centered Layout）**：

```text
┌──────────────────────────────────────────────────────────┐
│ ForgeShell                                               │
├──────────────────────────────────────────────────────────┤
│ Stage: DESIGN | Role: System Designer | Mode: AUTO       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│                  Chat / Event Stream                     │
│                                                          │
│   用户输入                                                │
│   Agent 输出                                              │
│   调度决策                                                │
│   错误 / 回流原因                                          │
│                                                          │
│                                                          │
├──────────────────────────────────────────────────────────┤
│ Status: RUNNING | Next: TESTING | Blocker: None          │
├──────────────────────────────────────────────────────────┤
│ > 输入需求或命令                                           │
└──────────────────────────────────────────────────────────┘
```

---

### 8.3 Layout 特点

* ❌ 无左右分栏（避免视线偏移）
* ✅ 用户视线始终集中在中轴
* ✅ 上下结构对称
* ✅ 状态信息集中在顶部与底部

---

## 9. Status Bar Design

### 顶部状态栏（主状态）

```text
Stage: IMPLEMENTING | Role: Implementation Engineer | Mode: AUTO
```

### 底部状态栏（运行信息）

```text
Status: RUNNING | Next: TESTING | Blocker: None
```

---

## 10. Interaction Model

### 默认模式（AUTO）

* 用户只需自然语言输入
* Orchestrator 自动选择角色
* 角色切换对用户隐式

---

### 显式控制模式（可选）

用户可手动控制：

```bash
/role
/switch solution
/lock
/unlock
/trace
/why
```

---

## 11. Role Visibility Policy

* 不在聊天流中频繁提示角色切换
* 当前角色仅在状态栏显示
* 用户可随时查询或控制

---

## 12. Command System

### 查询

```bash
/status
/role
/why
/trace
/history
```

### 控制

```bash
/switch <role>
/lock
/unlock
```

### 流程

```bash
/plan
/run
/retry
/rollback
/terminate
```

### 文档

```bash
/open spec
/open solution
/open design
/open test
```

---

## 13. Orchestration Logic

调度器决策基于：

### 1. 用户语义

* 提需求 / 改需求
* 问技术
* 修 bug
* 查测试

### 2. 当前状态

* REQUIREMENTS
* SOLUTION
* DESIGN
* IMPLEMENTING
* TESTING

---

## 14. Approval Points

关键阶段建议用户确认：

* 需求 → 技术方案
* 技术方案 → 系统设计
* 批量实现
* 回滚

---

## 15. Tech Stack (Suggested)

* Python
* Pydantic（后续用于正式 Schema）
* JSON / SQLite（状态）
* Textual（TUI）
* Rich（渲染）

---

## 16. Project Structure

```text
forgeflow/
├── agents/
│   ├── requirements_engineer.py
│   ├── solution_engineer.py
│   ├── system_designer.py
│   ├── implementation_engineer.py
│   ├── test_validation_engineer.py
│   ├── orchestrator.py
│   └── state_manager.py
├── schemas/
│   ├── spec.py
│   ├── solution.py
│   ├── design.py
│   ├── implementation.py
│   └── testing.py
├── state/
│   ├── spec.json
│   ├── solution.json
│   ├── system_design.json
│   ├── implementation_status.json
│   └── test_report.json
├── tui/
│   ├── app.py
│   ├── screens.py
│   ├── widgets.py
│   ├── commands.py
│   └── event_stream.py
├── main.py
└── README.md
```

---

## 17. MVP Scope

第一版只需实现：

* 聊天输入
* 自动角色调度
* 状态栏显示
* 基础 Spec → Solution → Design 流程
* `state/*.json` 的读写与阶段推进

---

## 18. Summary

ForgeFlow 不是一个聊天工具，而是：

> **一个由多 Agent 协同驱动的软件工程执行引擎**

ForgeShell 提供：

> **一个对用户透明、对系统可控的终端交互界面**

---

## 19. Key Insight

该系统的核心设计在于：

* **复杂性隐藏在后台**
* **状态暴露在前台**
* **控制权随时可取回**

---
