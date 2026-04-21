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

* 维护所有文档（Spec / Solution / Design / Test）
* 版本管理与 diff
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

---

## 7. Data Contracts

所有阶段必须输出结构化数据（JSON / Schema），禁止依赖纯文本。

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
* Pydantic（Schema）
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
