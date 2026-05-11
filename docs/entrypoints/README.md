# Entrypoint Docs

本页描述入口层边界，目标是避免出现第二控制面。

## 当前入口
- ForgeShell（TUI）：Primary UI 目标。
- CLI Runner（`main.py` / `forgeflow`）：当前开发与调试入口。

## 边界约束
- 两个入口都通过 Project Orchestrator 执行。
- Orchestrator 是唯一控制面。
- StateManager 是单一状态源。
- ForgeShell 允许只读展示状态与产物。
- ForgeShell 不允许直接写状态、不允许直接调 agent、不允许直接推进 stage、不允许直接执行 patch 或命令。

## 当前 TUI 命令
- `/status`
- `/open spec`
- `/open solution`
- `/open design`
- `/run`
- `/help`
- `/quit`

`/status` 当前仅做只读观测，输出阶段与决策，并补充 execution governance 可见性（implementation mode、approval artifact presence、apply plan presence、mutation enabled）。

以下命令当前不支持：
- `/rollback`
- `/retry`
- `/switch`
- `/lock`
- `/execute`
- `/apply`

## 当前运行命令

```bash
python3.11 main.py --auto-run "<requirement>"
python3.11 main.py --tui
forgeflow --tui
```

说明：当前不支持 `--input` 参数。

## Runtime Artifact Boundary
- 运行缓存默认不入库：`.forgeflow/state/`、`.forgeflow/generated/`、`.forgeflow/runs/`、`.forgeflow/tmp/`。
- 仓库根下运行输出默认不入库：`runs/*`、`tmp/`、`.tmp/`、`__tmp__/`。
- 人工整理评审产物可入库：`runs/manual_reviews/`。
