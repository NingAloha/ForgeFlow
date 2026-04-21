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

### 4.5 Test & Validation Engineer

执行功能测试、集成测试并进行问题归因。

---

## 5. Control Layer

### 5.1 Project Orchestrator

* 自动选择当前执行角色
* 控制流程推进 / 回流 / 重试
* 基于「用户语义 × 当前状态」做决策

### 5.2 State Manager

* 维护阶段状态文件（Spec / Solution / Design / Implementation / Test）
* 负责状态持久化与阶段交接
* 提供统一状态读取

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
* `risks`：当前方案的主要风险点。
* `alternatives`：被考虑过的备选方案及其取舍空间。

### 7.3 Design State

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
  "mvp_plan": {}
}
```

字段说明：

* `project_structure`：项目结构定义。
* `project_structure.directories`：目录级组织方式。
* `project_structure.modules`：模块级拆分结果，通常比 solution 里的 `module_mapping` 更具体。
* `contracts`：模块间接口契约、输入输出结构、调用边界。
* `data_flow`：数据或状态在系统中的流转路径。
* `mvp_plan`：最小可用版本的落地计划，用于约束第一阶段实现范围。

### 7.4 Implementation State

`state/implementation_status.json`

用于保存实现阶段产物，回答“当前代码实现到哪一步了”，重点是实际产出、测试和阻塞项。

```json
{
  "module_name": "",
  "implementation_status": "not_started",
  "files_created": [],
  "unit_tests": [],
  "contract_compliance": true,
  "known_limitations": [],
  "blockers": []
}
```

字段说明：

* `module_name`：当前实现对象，通常是一个模块、子系统或本轮任务名。
* `implementation_status`：当前实现状态，如 `not_started`、`in_progress`、`done`。
* `files_created`：本轮新增或修改的文件。
* `unit_tests`：本轮对应的单元测试或测试文件。
* `contract_compliance`：实现是否符合上游 design 定义的契约。
* `known_limitations`：已经知道但暂未解决的限制。
* `blockers`：阻塞继续实现的问题。

### 7.5 Testing State

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
