# ForgeFlow / ForgeShell

[English Overview](./docs/README.en.md)

一个以结构化状态驱动的多 Agent 软件工程流水线。

## 项目概览

ForgeFlow 试图把用户输入逐步推进为以下阶段产物：

* 需求规格（Requirements）
* 技术方案（Solution）
* 系统设计（Design）
* 代码实现（Implementation）
* 测试验证（Testing）

ForgeShell 是这个流程的主交互入口。它负责聊天式会话、状态可视化和持续交互；当前仓库里的 `main.py` 只保留为最小 CLI runner，用于直接触发一次 orchestrator 调度，并输出面向开发/诊断的诊断视图。

## 这是什么项目

这不是一个普通聊天工具。

它更接近一个工作流驱动的软件工程系统，核心由这些部分组成：

* 分层 agent：每层只负责一个阶段
* 控制层：负责流程调度与阶段切换
* 状态层：负责结构化状态持久化
* 交互入口层：TUI 作为产品入口，CLI 作为开发与诊断入口

## 架构快照

```text
ForgeShell (Primary UI) ─┐
                         ├── Project Orchestrator
CLI Runner (Dev / Debug) ┘
                             ├── State Manager
                             ├── Requirements Engineer
                             ├── Solution Engineer
                             ├── System Designer
                             ├── Implementation Engineer
                             └── Test & Validation Engineer
```

## 核心理念

* 分层职责：每个 agent 只负责一层
* 契约驱动：阶段之间通过结构化状态交接
* 默认自动调度：正常使用应尽量自然
* 保留显式控制：用户仍可查看、切换、锁定和干预
* 状态透明：系统应展示进度，但不增加噪音

## 仓库结构

```text
forgeflow/
├── docs/
├── agents/
├── schemas/
├── state/
├── tui/
├── main.py
└── README.md
```

目录说明：

* [docs/](./docs/README.md)：详细流程规则与状态契约文档
* [agents/](./agents/README.md)：agent 与控制层职责说明
* [state/](./state/README.md)：阶段状态文件
* [schemas/](./schemas/README.md)：后续正式 schema 层
* [main.py](./main.py)：开发与诊断用的最小 CLI runner，用于直接运行一次 orchestrator 并输出诊断视图
* [tui/](./tui/README.md)：ForgeShell 主交互入口与终端 UI 层

## 阅读路径

如果你是第一次看这个项目，建议按下面顺序读：

1. 当前 `README`
2. [docs/README.md](./docs/README.md)
3. [agents/README.md](./agents/README.md)
4. [state/README.md](./state/README.md)

详细参考：

* [docs/workflow_criteria.md](./docs/workflow_criteria.md)：单线程主流程阶段判定规则
* [docs/agent_design_principles.md](./docs/agent_design_principles.md)：后续 agent 能力扩展与动作空间设计原则
* [docs/state_contracts.md](./docs/state_contracts.md)：各阶段 JSON 状态契约

## 当前范围

当前 MVP 方向包括：

* ForgeShell 作为主交互入口
* 最小 CLI runner 作为开发/诊断入口
* 自动角色调度
* 可见的流程状态
* 单线程主流程：requirements -> testing
* 基于 JSON 的阶段状态管理

## 当前适用范围与限制

当前这套工作流更适合：

* 新项目，或一轮边界相对独立的功能交付
* 能够较早收敛“本轮需求”的场景
* 围绕单条主线闭环推进的开发过程

当前它还不适合直接当作以下场景的完整模型：

* 长期演进中的存量项目
* 多需求并行推进
* 边开发边持续插入新需求
* 一套状态同时管理多个 feature stream、多个版本线或 backlog 驱动的持续迭代

换句话说，当前模型更接近“单轮需求闭环驱动”的工程工作流，而不是一个已经完整覆盖增量开发和长期项目管理的系统。详细边界见 [docs/workflow_scope.md](./docs/workflow_scope.md)。

## 当前状态

当前仓库已经完成的文档整理：

* 阶段判定规则已拆到 `docs/`
* 状态 JSON 契约已收紧并文档化
* 已补充一版 agent 设计原则文档，用于约束后续演进方向
* 各模块目录已补充导航 README
* `main.py` 已可直接触发一次 orchestrator 调度，并输出诊断视图
* requirements 阶段已能生成首版 `spec` 核心字段，并在缺信息时写入 `question_state`
* `question_state = answered` 时，控制层会重新执行对应阶段来消费回答，而不是继续卡在等待态
* 实现仍处于早期阶段

## 给第一次阅读的人

第一次看这个仓库时，先抓住三件事：

* 每一层分别负责什么
* 状态如何在阶段之间流动
* 控制层和执行层 agent 的边界是什么

除非你准备实现 orchestrator 或 state manager，否则不要先从详细判定条件开始读。
