# ForgeFlow

ForgeFlow 是一个以 Contract（契约）、Artifact（工件）、Verification（验证）和 Revision（版本修订）为核心的软件工程系统。

它并不是一个“万能 AI 自动编程 Agent”。

ForgeFlow 更接近：

```text
用户意图
→ 不断规格化
→ 不断稳定化
→ 最终形成可验证实现
```

系统中的每一层都像一层“筛子”：

- 筛掉模糊需求
- 筛掉隐式假设
- 筛掉不一致结构
- 筛掉不可验证实现

最终只允许满足约束的 artifact 继续向下流动。

---

# 核心理念

传统 Agent 系统经常出现：

- agent 边界漂移
- workflow 语义失控
- runtime 黑箱化
- retry 造成 semantic drift
- hidden assumptions 不断积累

最终系统会进入：

```text
看起来在运行
但没人真正知道系统语义
```

ForgeFlow 尝试通过以下方式避免这种崩塌：

- 显式 artifact
- 显式 contract
- 显式 ownership
- 显式 assumption
- 显式 failure attribution
- 显式 revision history

---

# 系统结构

ForgeFlow 是一个“多层语义筛选系统”。

```text
User Intent
  ↓
Requirements Sieve
  ↓
Design Sieve
  ↓
Test Sieve
  ↓
Implementation Sieve
  ↓
Verification Sieve
```

每一层：
- 接收 artifact
- 检查语义合法性
- 输出更稳定的 artifact

ForgeFlow 的核心不是：
- workflow orchestration
- autonomous agents

而是：

```text
artifact stabilization
```

---

# 核心 Ontology

## RequirementSpec

用户需求的结构化表示。

包含：

- goals
- functional requirements
- constraints
- acceptance criteria
- unresolved items
- assumptions

RequirementSpec 必须足够规格化后才能进入 Design 阶段。

---

## ModuleContract

模块的行为契约。

定义：

- 输入格式
- 输入范围
- 数据处理语义
- 输出格式
- rejection conditions

不定义：

- 文件结构
- 函数名
- 算法
- runtime
- library

因为这些属于 implementation world。

---

## ContractGraph

模块之间的契约关系图。

定义：

- 模块依赖关系
- 数据流
- compatibility constraints
- integration expectations

---

## TestSuite

由 contract 自动生成的模块测试。

验证：

- 输入输出行为
- rejection behavior
- semantic expectations

---

## IntegrationTestSuite

多模块协作测试。

验证：

- contract compatibility
- integration correctness
- cross-module behavior

---

## VerificationResult

结构化验证结果。

包含：

- passed tests
- failed tests
- semantic verification status
- coverage information

---

## FailureReport

失败归因对象。

ForgeFlow 禁止“盲目 retry”。

任何失败都必须先归因：

```yaml
attribution:
  - implementation_error
  - test_error
  - contract_error
  - requirement_error
```

只有归因后，系统才允许 rollback。

---

## Assumption

显式假设。

ForgeFlow 不允许 hidden assumptions。

所有：
- 默认值
- 推断条件
- 未定义行为

都必须成为 artifact。

---

# Agents

ForgeFlow 中的 Agent 不是“人格化智能体”。

它们更接近：

```text
受限 artifact transformer
```

---

## RequirementsAgent

负责：

```text
User Intent
→ RequirementSpec
```

职责：

- 发现模糊需求
- 请求用户澄清
- 显式记录 unresolved items
- 在必要时生成 assumptions

不能：

- 写 implementation
- 生成 contracts
- 决定 architecture

---

## DesignAgent

负责：

```text
RequirementSpec
→ ModuleContracts + ContractGraph
```

职责：

- 划分模块边界
- 生成模块 contract
- 定义 integration graph

拥有：

- contract ownership
- graph ownership

---

## TestAgent

负责：

```text
ModuleContract
→ Module TestSuite
```

职责：

- 根据 contract 生成测试
- 验证 rejection behavior
- 保持 semantic expectations

不能修改 contract。

---

## IntegrationAgent

负责：

```text
ContractGraph
→ Integration TestSuite
```

职责：

- 验证模块兼容性
- 验证 integration correctness

不能修改 contract。

---

## ImplementAgent

负责：

```text
Contracts + Tests
→ Source Code
```

职责：

- 根据 contract 和 tests 实现代码
- 持续运行测试

不能修改：
- contracts
- tests

---

# Runtime

ForgeFlow Runtime 是：

```text
受控 artifact 状态机
```

而不是：

- autonomous orchestrator
- reasoning engine
- AI planner

职责：

- 调用 agent
- 控制写权限
- 管理状态转移
- 运行测试
- 管理 rollback
- 生成 git commit
- 保存 revision history

---

# Git

Git 在 ForgeFlow 中不是简单版本管理工具。

Git 是：

```text
semantic revision ledger
```

系统中的每个重要 transition 都必须形成 revision：

- requirement revision
- contract revision
- test generation
- implementation iteration
- verification failure

---

# Failure Handling

ForgeFlow 禁止：

```text
失败
→ 无限 retry
→ 随机修改
```

正确流程：

```text
失败
→ FailureReport
→ Attribution
→ 精确 rollback
```

例如：

```text
Implementation fails
→ implementation_error
→ retry implementation

Tests inconsistent with contract
→ test_error
→ regenerate tests

Contract impossible to satisfy
→ contract_error
→ rollback to DesignAgent

Requirement itself contradictory
→ requirement_error
→ rollback to RequirementsAgent
```

---

# 最小项目结构

```text
project/
├── requirements/
│   └── requirement_spec.yaml
│
├── modules/
│   ├── parser/
│   │   ├── contract.yaml
│   │   ├── tests/
│   │   ├── src/
│   │   └── verification/
│   │
│   └── summarizer/
│       ├── contract.yaml
│       ├── tests/
│       ├── src/
│       └── verification/
│
├── integration/
│   ├── contract_graph.yaml
│   ├── tests/
│   └── verification/
│
├── revisions/
│
└── runtime/
```

---

# 当前目标

ForgeFlow 当前阶段专注于：

- ontology stabilization
- contract refinement
- artifact semantics
- verification structure
- revision discipline

当前刻意避免：

- 黑箱 autonomous orchestration
- 无约束 code generation
- 不可追踪 reasoning
- semantic drift

ForgeFlow 目前最重要的问题不是：

```text
能不能自动写代码
```

而是：

```text
能不能形成稳定、可验证、可回滚、可追踪的软件工程语义系统
```