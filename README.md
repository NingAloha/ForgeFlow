# ForgeFlow

[English version](./README_EN.md)

> TL;DR  
> ForgeFlow 是面向 AI 软件工程流程的有状态 orchestration runtime。  
> 它重点解决 workflow 可复现性、阶段稳定性与 artifact 可验证性，  
> 而不是替代 coding agents 本身。

## 项目定位
AI coding 的主要问题通常不是“生成不出代码”，而是工程流程不稳定：

- workflow 不可复现
- 阶段推进隐式漂移
- artifact 语义不稳定
- 执行路径缺乏可验证边界

ForgeFlow 针对的是这个问题域：把 AI 软件工程从“提示词序列”改造成“有状态、可回放、可验证”的工程流程。

ForgeShell 是主界面（Primary UI）目标；CLI Runner 是当前可运行的开发/调试入口。

- ForgeFlow 不替代 coding agents，而是在 agents 外层提供可复现的 orchestration runtime。
- ForgeFlow 假设：未经约束的 workflow flexibility 最终会演化为工程不稳定。

## 设计原则
- 显式性优于智能性（explicit workflow semantics over implicit agent behavior）
- 先收敛语义，再扩展能力（runtime-first, capability-second）
- Fail closed 优于 silent fallback

## 当前承诺（可验证）
- 显式阶段（explicit stages）
- 显式产物契约（artifact contracts）
- 可回放运行轨迹（replayable runs）
- 可追踪产物依赖（lineage）
- 受治理的执行边界（mutation gating）

## 非目标（当前明确不做）
- 不追求 uncontrolled autonomy
- 不在当前阶段开放 execution mutation
- 不把所有 runtime decision 立即声明化
- 不把 ForgeFlow 定义为“another agent framework”

## 当前范围（v0.2.x）

### 已完成（第一阶段解耦闭环）
- PR1：SE 工作流事实已声明到 manifest
- PR2：Orchestrator 的 agent 绑定已改为 manifest 驱动
- PR3：runtime lineage 依赖已改为 manifest 驱动
- PR4：profile/runtime decoupling boundary 已文档化

### 当前不做（刻意边界）
- 不改 `StageEvaluator`
- 不改 backflow / question flow
- 不开放 execution mutation（仍 blocked）

### 下一步唯一目标（待启动）
- PR5：declared forward transitions read path（前向 transitions 读取路径声明化）
- 验收目标：行为零变化 + `pytest -q` 全绿

- ForgeFlow 不是“自动写代码系统”的完整替代。
- ForgeFlow 当前重点是 workflow semantics 的结构稳定性与可验证性。
- ForgeFlow SE 是第一个 target profile：软件工程 workflow。

## 当前架构

```text
ForgeShell (主界面 / Primary UI) ─┐
                         ├── Project Orchestrator
CLI Runner (Dev / Debug) ┘
                             ├── State Manager
                             ├── Profile Registry
                             │     └── ForgeFlow SE Manifest
                             │           ├── stage_agents
                             │           ├── stage_produces
                             │           ├── transitions
                             │           └── lineage_dependencies
                             ├── StageEvaluator
                             └── SE Agents（由 manifest stage_agents 绑定）
                                   ├── Requirements Engineer
                                   ├── Solution Engineer
                                   ├── System Designer
                                   ├── Implementation Engineer
                                   └── Test & Validation Engineer
```

边界说明（防误读）：

- manifest 还不是所有 runtime 决策的唯一真相源；它只对当前列出的消费面负责。
- 当前已 manifest-driven 的消费面：
  - Orchestrator 使用 `stage_agents` 完成 agent 绑定
  - runtime lineage 使用 `lineage_dependencies`
- 仍故意未声明化：`StageEvaluator` / backflow / question flow / execution

继续阅读：`docs/profile-runtime.md`

## 系统组成
- **ForgeFlow Core**：控制面语义收敛（state / events / replay / governance / approvals）
- **ForgeFlow SE**：第一个 profile，定义 SE workflow 的阶段与产物约束
- **ForgeFlow Skills**：局部、可替换的操作能力
- **ForgeShell**：human-in-the-loop 交互与观测入口

## 入口边界
- ForgeShell 是主交互界面目标，CLI Runner 是开发/调试入口。
- 两个入口都通过 Project Orchestrator 执行流程。
- Orchestrator 是唯一控制面，StateManager 是单一状态源。
- TUI 可只读展示状态，但不得绕过 Orchestrator 做写操作、阶段推进、agent 调用、patch 应用或命令执行。
- 当前 TUI 支持命令仅有：
  - `/status`
  - `/open spec`
  - `/open solution`
  - `/open design`
  - `/run`
  - `/help`
  - `/quit`

## 当前能力
- `main.py` 支持一次调度与 `--auto-run` 连续推进。
- `--tui` 可启动最小 ForgeShell 终端壳。
- requirements/solution/design/implementation/testing 均已接入主链路。
- implementation 当前产出是交接信息与预览信息，不是实际代码落盘。

## Runtime Model
ForgeFlow 的架构方向是 runtime-first：优先把可治理、可回放、可审计的 runtime 语义收敛清楚，
再在明确边界内逐步引入执行能力（governed execution）。

- **Core Runtime**：收敛 replay、lineage、approvals 与执行边界等 runtime control plane 语义。
- **Profiles**：定义领域工作流形态；ForgeFlow SE 是第一个 profile（软件工程 pipeline）。
- **Skills**：提供局部、可替换的操作能力（工具化能力），用于支撑 profile 的具体运行需求。

继续阅读：
- [docs/runtime-theory.md](./docs/runtime-theory.md)
- [docs/runtime-theory.en.md](./docs/runtime-theory.en.md)

## Runtime Principles
- State is explicit.
- Replay is read-only.
- Events are append-only.
- Execution is governed.
- Runtime artifacts are auditable.
- Human approval is first-class.

### 当前能力边界矩阵
| 能力 | 当前状态 |
| --- | --- |
| Planning（Requirements/Solution/Design） | ✅ |
| Implementation Handoff | ✅ |
| Reviewable Execution Contract | ✅ |
| Approval Semantics | ✅ |
| Dry-run Apply Plan | ✅ |
| Real Mutation Runtime | ❌ |
| Patch Apply | ❌ |
| Command Execution | ❌ |

## 实现模式（Implementation）
- `handoff`：默认稳定路径，输出 implementation checklist / done criteria / suggested tests / blockers。
- `execute`：当前仅预览，返回 `blocked` 与 reviewable execution contract，不触发真实 mutation。

执行治理细节（approval artifact / gate / dry-run apply plan / 校验规则）已下沉到文档：  
- [docs/implementation-governance.md](./docs/implementation-governance.md)
- [docs/profile-runtime.md](./docs/profile-runtime.md)

## 快速开始
安装开发依赖（可编辑模式）：

```bash
python3.11 -m pip install -e ".[dev]"
```

常用入口：

```bash
python3.11 main.py --auto-run "<requirement>"
python3.11 main.py --tui
forgeflow --tui
```

说明：
- `user_input` 当前通过位置参数传入。
- 当前不支持 `--input` 参数。

当前质量门禁：
- `ruff check .`
- `pytest -q`

## 当前限制
- execute 模式尚未开放真实执行能力。
- patch preview / patch draft 仅用于设计与实现交接预览。
- 多轮自动修复、真实 patch 落盘与命令执行仍未开放。

## 路线图
- 强化 LLM fallback policy consistency。
- 在不破坏主 flow 的前提下，逐步引入安全可审计的执行能力。
- 保持 Orchestrator 单控制面，不把 TUI 扩成第二控制面。

## 更多文档
- Runtime root / materialized cache / 运行产物边界：`docs/runtime-v0-architecture.md`
- 分支协作边界：`docs/branch-boundaries.md`、`docs/git-workflow.md`
- 执行治理与可审阅执行契约：`docs/implementation-governance.md`
- profile/runtime 边界：`docs/profile-runtime.md`

## 英文版本
英文开发者概览见 [README_EN.md](./README_EN.md)。
