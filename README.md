# **ForgeFlow**

### A Multi-Agent Software Engineering Pipeline

---

## 1. Overview

**ForgeFlow** 是一个多 Agent 协同的软件工程流水线系统，用于将用户需求从自然语言逐步转化为：

* 结构化需求（Specification）
* 技术方案（Solution）
* 系统结构（System Design）
* 代码实现（Implementation）
* 测试验证（Testing）

系统核心特征：

* **分层明确（Spec → Solution → Design → Implementation → Testing）**
* **强契约驱动（Contract-driven）**
* **可回流（Rollback-capable）**
* **状态可追踪（Stateful pipeline）**

---

## 2. Core Principles

### 2.1 Separation of Concerns

每个 Agent 仅负责单一职责，禁止跨层决策。

### 2.2 Contract First

所有阶段通过**结构化契约（Schema）**衔接，而非自由文本。

### 2.3 Controlled Feedback Loop

系统支持回流，但必须通过调度器控制。

### 2.4 Single Source of Truth

所有状态与文档由统一状态管理层维护。

---

## 3. System Architecture

### 3.1 Pipeline Structure

```
User
 ↓
Requirements Engineer
 ↓
Solution Engineer
 ↓
System Designer
 ↓
Implementation Engineer
 ↓
Test & Validation Engineer
```

### 3.2 Control Layer

```
Orchestrator (流程控制)
State Manager (状态与文档管理)
```

---

## 4. Agent Definitions

---

### 4.1 Requirements Engineer

**Objective**
将用户需求转化为结构化、可验证的需求规格。

**Input**

* 用户原始需求
* 多轮澄清结果

**Output (Spec)**

* project_goal
* functional_requirements
* non_functional_requirements
* constraints
* acceptance_criteria
* open_questions

**Boundary**

* 不涉及技术实现
* 不设计系统结构

---

### 4.2 Solution Engineer

**Objective**
基于需求规格设计技术方案与技术选型。

**Input**

* 需求规格（Spec）

**Output**

* 技术栈选择
* 模块能力映射
* 技术风险与替代方案

**Boundary**

* 不涉及具体代码
* 不定义接口细节

---

### 4.3 System Designer

**Objective**
将技术方案转化为系统结构与接口契约。

**Input**

* 技术方案

**Output**

* 模块划分
* 接口契约（Contracts）
* 数据流设计
* 项目骨架（Scaffold）
* MVP（最小可运行验证）

**Boundary**

* 不实现业务逻辑
* 只做结构与契约

---

### 4.4 Implementation Engineer

**Objective**
根据模块契约实现代码并完成单元测试。

**Input**

* 模块契约
* 项目结构

**Output**

* 模块代码
* 单元测试
* 实现说明
* 阻塞问题

**Boundary**

* 不修改需求或架构
* 必须遵守契约

---

### 4.5 Test & Validation Engineer

**Objective**
验证模块功能与系统联动，并进行问题归因。

**Input**

* 模块代码
* 单元测试结果
* 接口契约

**Output**

* 功能测试
* 集成测试
* 测试报告
* 问题归因报告

**Boundary**

* 不修改代码
* 负责归因与反馈

---

## 5. Control Layer

---

### 5.1 Orchestrator

**Role**
控制系统执行流程。

**Responsibilities**

* 阶段推进（forward）
* 回流（rollback）
* 重试（retry）
* 终止（terminate）

**Decision Examples**

* 测试失败 → 回 Implementation 或 System Design
* 结构不合理 → 回 Solution Engineer

---

### 5.2 State Manager

**Role**
维护所有文档与状态。

**Responsibilities**

* 版本控制
* 文档存储
* 状态查询
* diff 分析

**Managed Artifacts**

* spec.json
* solution.json
* system_design.json
* implementation_status.json
* test_report.json

---

## 6. State Machine

### 6.1 Main Flow

```
INIT
→ REQUIREMENTS_READY
→ SOLUTION_READY
→ DESIGN_READY
→ IMPLEMENTING
→ TESTING
→ DONE
```

---

### 6.2 Rollback Rules

| Failure Type | Rollback Target         |
| ------------ | ----------------------- |
| Spec 不完整     | Requirements Engineer   |
| 技术不可行        | Solution Engineer       |
| 结构不支持实现      | System Designer         |
| 单模块错误        | Implementation Engineer |
| 多模块联动错误      | System Designer         |
| 架构问题         | Solution Engineer       |

---

## 7. Data Contracts (Schemas)

所有 Agent 之间的数据必须结构化，例如：

```json
{
  "module": "auth_service",
  "inputs": {"username": "string"},
  "outputs": {"token": "string"},
  "constraints": ["must validate password"]
}
```

禁止使用非结构化自由文本作为核心数据。

---

## 8. Minimal Implementation Strategy

### 技术建议

* Python
* Pydantic（Schema定义）
* JSON（状态存储）
* 自定义 Orchestrator（状态机）

---

### 推荐目录结构

```
project/
├── agents/
├── schemas/
├── state/
├── orchestrator/
├── main.py
```

---

## 9. Key Advantages

* 清晰的职责划分
* 可扩展的 Agent 架构
* 可回溯的工程流程
* 接近真实软件工程体系

---

## 10. Limitations

* 初期实现复杂度较高
* 需要严格的契约约束
* Agent 协调成本较高

---

## 11. Future Extensions

* 自动化测试生成
* RAG 知识增强
* UI 可视化流程
* 多项目并行调度
* Agent 自学习能力

---

## 12. Summary

ForgeFlow 的本质不是“AI 对话系统”，而是：

> **一个结构化的软件工程执行引擎，由多个具备明确职责的 Agent 协同完成复杂任务。**

---
