# 分支边界规则

本文件定义当前开发分支与目录范围的对应关系，并由 CI 路径守卫执行。

## 分支类型

### `track/orchestrator`
- 允许改动：
  - `agents/orchestrator/**`
  - `tests/unit/orchestrator/**`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/implementation-governance`
- 允许改动：
  - `agents/implementation_engineer/**`
  - `schemas/implementation.py`（例外路径：仅 execution governance contract/schema 扩展）
  - `tests/unit/agents/test_implementation_engineer.py`
  - `tests/unit/agents/test_execution_*.py`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/orchestrator/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/testing-semantics`
- 允许改动：
  - `agents/test_validation_engineer/**`
  - `tests/unit/agents/test_test_validation_engineer.py`
  - `tests/unit/agents/test_agent_integration.py`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/orchestrator/**`
  - `agents/implementation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/tui-observability`
- 允许改动：
  - `tui/**`
  - `tests/unit/entrypoints/test_tui.py`
  - `tests/unit/entrypoints/test_status_overview.py`
  - `main.py`（仅只读入口与观测输出）
  - `forgeflow/runtime/**`（只读 status snapshot/render 模块）
  - `forgeflow/__init__.py`
  - `pyproject.toml`（例外路径：仅允许 package discovery include 调整；不代表放开 CLI entrypoint / package migration）
  - `agents/orchestrator/**`（仅只读查询相关改动）
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `schemas/**`

### `track/artifact-lineage-foundation`
- 允许改动：
  - `agents/orchestrator/**`
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `tests/unit/orchestrator/test_core.py`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/human-workflow-semantics`
- 允许改动：
  - `agents/orchestrator/**`
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `tests/unit/orchestrator/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `README.md`
  - `README_EN.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/runtime-index-repair`
- 允许改动：
  - `main.py`（仅 repair/rebuild index 的显式命令入口）
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/review-decision-artifacts`
- 允许改动：
  - `main.py`（仅写入 review_state.json 的显式命令入口）
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/review-approval-bridge`
- 允许改动：
  - `forgeflow/runtime/**`（只读展示：review queue + approvals 聚合）
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `main.py`

### `track/docs-review`
- 允许改动：
  - `README.md`
  - `README_EN.md`
  - `docs/**`
  - `runs/manual_reviews/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `tests/**`
  - `schemas/**`

## 通用规则
- `main` 仅通过 PR 合并，不直接开发。
- CI 需通过 `ruff check .`、`pytest -q`、分支路径守卫。
- 如需跨轨道改动，请拆成多个 PR，不在单个 PR 混改。
