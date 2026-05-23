# ForgeFlow

[English version](./README_EN.md)

> TL;DR  
> ForgeFlow 是面向 AI 辅助软件开发的 **engineering state system**。  
> 它把 “项目当前处于哪个工程阶段、哪些结论有证据、失败该回退到哪一层”  
> 这些工程认知状态收敛为结构化产物与可审计证据，而不是靠 prompt 记忆。

## 1. Problem / Failure Model
现代 AI coding agents 往往能在局部推进（写出一段可运行代码、修一个报错、补一个模块），
但难以在长周期项目中维持稳定、可追溯、可回退的 **系统级 engineering state**。

常见失效模式不是 prompting 失败，而是 **engineering state continuity failures**：

- requirement drift：需求口径在推进中被悄然改写
- architecture erosion：局部实现不断堆叠，系统结构逐渐失真
- pseudo-completion：LLM 声称完成，但缺少可执行证据/可追溯链路
- context fragmentation：团队/模型上下文不断丢失，无法回答“现在到底做到哪了”
- broken traceability：需求/设计/实现/测试之间缺少结构化链接
- 文档与实现漂移：过期架构假设被文档固化，artifact 与 runtime evidence 脱节
- irreversible mutation：变更不可审计、不可复现，回退成本不确定
- rollback ambiguity：失败后不知道应该回退到 requirements / design / implementation / testing 的哪一层

ForgeFlow 把这些视为 **工程状态连续性问题**（state 丢失 / state 漂移 / 证据缺失），
而不是“模型不够聪明/提示词不够好”的问题。

## 2. What ForgeFlow Is
ForgeFlow 是一个工程状态系统（engineering state system），用于 AI 辅助软件开发中的 staged progression：

```text
Requirements → Solution / Architecture → Design → Implementation → Testing
```

它的 primary object 是：

> project engineering state（项目工程状态）

ForgeFlow 管理的不是“软件绝对正确性”，而是系统当前“哪些内容已经被说明/设计/实现/验证”，并将这些状态尽可能绑定到：

- structured artifacts（结构化 JSON 产物）
- runtime evidence（运行轨迹、诊断信息）
- lineage / traceability links（可追溯链接）
- review / approvals（可审阅、可审批的证据链）

注意：ForgeFlow **Git-aware**，并且设计方向是把工程状态绑定到 Git snapshots / recovery points；但当前版本并不把 “completed node → Git commit” 作为已实现保证。

## 3. What ForgeFlow Is Not
ForgeFlow 不是：

- 通用 workflow engine / DAG orchestration 框架
- multi-agent framework（也不是 LangGraph / CrewAI / AutoGen 的替代品）
- prompt chain manager
- coding agent 本身或 Claude Code replacement

在 ForgeFlow 中，“agents” 更接近实现细节：它们是各阶段状态的 **state producers**，而不是系统的 primary abstraction。

## 4. Core Model
- **Staged progression**：通过结构化状态把 Requirements/Solution/Design/Implementation/Testing 各层显式化，并由 orchestrator 基于状态判定推进/回流。
- **Completion semantics**：阶段不因 LLM 声称完成而完成；完成必须可由结构化状态判断（schema-valid / structurally complete / traceable where possible）。
- **Failure attribution → rollback target（概念层）**：测试失败不只标记 fail，而应归因并指向回退层级；当前仓库已对部分回流规则进行了文档化与实现（见 docs）。
- **Agents as producers**：每个阶段的 agent 负责产出/更新该阶段的结构化 state；orchestrator 负责阶段决策与治理边界。

## 5. Artifacts and Evidence
ForgeFlow 的证据不是单一来源，而是一个强度梯度（从软到硬）：

- **Soft evidence**：LLM 的自述/评审意见（只能作为辅助，不能直接叫 verified）
- **Stronger evidence**：结构化 artifacts、可追溯链接（lineage）、运行事件与诊断、review/approval 记录
- **Harder evidence（当可用时）**：可执行 tests / commands 的真实运行结果、退出码、测试数量、失败列表等
- **Git snapshots（设计方向）**：Git 提供可恢复的文件系统快照基底；ForgeFlow 负责表达工程语义状态与证据绑定。当前不把 Git commit 等同于工程状态，也不把 Git checkpoint/rollback 当作已实现能力。

你可以直接检查仓库输出的证据产物（已实现）：
- `.forgeflow/state/*.json`：阶段状态（spec/solution/system_design/implementation_status/test_report/question_state）
- `.forgeflow/runs/<run_id>/`：运行证据（`summary.json` / `events.jsonl` / `lineage.json` / `review_state.json` / `approvals/*.json` 等）

## 6. Current guarantees and boundaries
### Implemented today（可验证）
- 显式阶段与结构化状态文件（state JSON contracts + schema validation）
- 可回放的运行轨迹与 runtime artifacts（events/summary/lineage/review/approvals 等）
- 受治理的执行边界与 execution preview（mutation 仍 disabled by design）
- 回流/停留的规则与诊断输出（以结构化状态为主输入）

### Designed direction（明确方向，但不作为已实现保证）
- 更细粒度的证据绑定（把更多“完成语义”绑定到可执行证据与可追溯链）
- 将工程状态与 Git 恢复点建立更直接的绑定关系（checkpoint metadata / recovery points）
- 更通用、profile 化的状态契约与治理语义

### Not yet implemented（当前明确没有）
- 自动 patch apply / 真实命令执行
- 自动 rollback / completed node → Git commit 的强绑定
- 以“层内并行节点 + layered stage tree schema”为核心的状态建模（当前仍以单线 staged progression 为主）

进展与边界细节：
- profile/runtime 边界与当前已声明消费面：`docs/profile-runtime.md`
- 方向与版本路线：`docs/roadmap.md`

### 范围边界
- ForgeFlow 不是“自动写代码系统”的完整替代。
- ForgeFlow 当前重点是工程认知状态的结构稳定性与证据绑定，而不是扩 agent 能力。
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

## 系统组成（实现分层，而非 primary abstraction）
- **ForgeFlow Core**：控制面语义收敛（state / events / replay / governance / approvals）
- **ForgeFlow SE**：第一个 profile，定义 SE staged progression 的阶段与产物契约
- **ForgeFlow Skills**：局部、可替换的操作能力
- **ForgeShell**：human-in-the-loop 交互与观测入口（目标入口；当前可运行入口仍以 CLI 为主）

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

## 当前能力（运行入口）
- `main.py` 支持一次调度与 `--auto-run` 连续推进。
- `--tui` 可启动最小 ForgeShell 终端壳。
- requirements/solution/design/implementation/testing 均已接入主链路（以结构化状态交接）。
- implementation 当前产出是交接信息与执行预览信息，不是实际代码落盘。

## 当前能力边界矩阵（可验证）
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

## 7. Quickstart
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

## 8. Docs map
- Runtime root / materialized cache / 运行产物边界：`docs/runtime-v0-architecture.md`
- 分支协作边界：`docs/branch-boundaries.md`、`docs/git-workflow.md`
- 执行治理与可审阅执行契约：`docs/implementation-governance.md`
- profile/runtime 边界：`docs/profile-runtime.md`
- Runtime 理论与方向（含 “已实现 vs 可能方向” 区分）：`docs/runtime-theory.md`
- 工作流规则与回流说明：`docs/workflow/README.md`
- 状态契约入口：`docs/state/README.md`
- Case studies：`docs/case-studies/forgeflow-self-realignment.md`

## 英文版本
英文开发者概览见 [README_EN.md](./README_EN.md)。
