# ForgeFlow

[English version](./README_EN.md)

## 项目定位
ForgeFlow 是一个以结构化状态驱动的软件工程流水线。当前目标是把用户输入沿着固定阶段推进：
`Requirements -> Solution -> Design -> Implementation -> Testing`。

ForgeShell 是 Primary UI 目标；CLI Runner 是当前可运行的开发/调试入口。

## 当前架构

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

## Implementation 模式
- `handoff`（默认稳定路径）：
  - 承接 `system_design`
  - 输出 implementation checklist、done criteria、suggested tests、blockers
- `execute`（当前 disabled 的预览路径）：
  - 返回 `blocked`
  - 返回 `patch preview generated`
  - 返回 `single-module patch draft generated`
  - `no mutation performed`

## Execution / Patch 边界
当前不做真实代码写入，不做 patch apply，不运行真实 Code Agent。

`execute` 模式当前只做 dry-run 预览：
- patch preview：目录级预览，不落盘，不执行命令。
- patch draft：
  - 仅首个 design module
  - unified diff 草案
  - create-only
  - 仅 README 占位文件
  - 不生成 Python 业务代码
  - 不写入文件
  - 不执行命令

## Reviewable Execution Contract
- `execute` 路径会输出可审阅的 execution contract，但当前仍是 `blocked`。
- contract 是 review object，不是 apply object。
- patch preview 与 patch draft 是同一 contract 的两种视图：
  - contract 块描述执行意图、边界与回滚预期（key-value）。
  - patch draft 块描述 unified diff 草案（仅预览，不落盘）。
- 未来 apply/rollback/testing 会复用这套 contract 语义，避免 preview/apply/rollback 语义分裂。

## Runtime Artifact Boundary
- 以下属于 runtime cache，不应入库：
  - `.forgeflow/state/`
  - `.forgeflow/generated/`
  - `.forgeflow/runs/`
  - 仓库根下非人工整理的运行输出（例如 `runs/*` 中的临时运行文件）
  - 系统临时目录中的 ` /tmp/forgeflow_* `（仓库外，不纳入版本管理）
- 以下属于 repository knowledge，应保留：
  - `runs/manual_reviews/`（人工整理的评审与对比产物）
- 约束目标：避免 patch preview / generated / run summary 的运行时噪音污染仓库历史。

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

## Roadmap
- 强化 LLM fallback policy consistency。
- 在不破坏主 flow 的前提下，逐步引入安全可审计的执行能力。
- 保持 Orchestrator 单控制面，不把 TUI 扩成第二控制面。

## English version
英文开发者概览见 [README_EN.md](./README_EN.md)。
