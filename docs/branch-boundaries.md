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

### `track/execution-gate-diagnostics`
- 允许改动：
  - `main.py`（只读 gate diagnostics 命令入口）
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

### `track/execution-gate-diagnostics-v2`
- 允许改动：
  - `main.py`（只读 gate diagnostics 命令入口）
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

### `track/execution-eligibility-split`
- 允许改动：
  - `main.py`（execution gate eligibility split / diagnostics）
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

### `track/sandbox-preview-materialization`
- 允许改动：
  - `main.py`（sandbox preview materialization entrypoint）
  - `forgeflow/runtime/**`（governed writes limited to `.forgeflow/generated/<run_id>/`）
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/replay-materialization-rendering`
- 允许改动：
  - `main.py`（replay CLI rendering; read-only）
  - `forgeflow/runtime/**`（replay rendering of execution_preview + timeline）
  - `tests/unit/runtime/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/runtime-event-taxonomy-cleanup`
- 允许改动：
  - `agents/orchestrator/**`（event taxonomy: step_finished / run_finished）
  - `forgeflow/runtime/**`（event allowlist + replay rendering compatibility）
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/materialization-failure-semantics`
- 允许改动：
  - `main.py`（sandbox preview materialization entrypoint; failure semantics）
  - `forgeflow/runtime/**`（execution_preview status + failed attempt recording）
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/lineage-invalidation-metadata`
- 允许改动：
  - `agents/orchestrator/**`（仅 lineage invalidation metadata 写入）
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `tests/unit/orchestrator/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/implementation_engineer/**`
  - `agents/test_validation_engineer/**`
  - `tui/**`
  - `schemas/**`

### `track/needs-rerun-diagnostics`
- 允许改动：
  - `forgeflow/runtime/**`（needs_rerun 只读诊断）
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

### `track/execution-contract-manifest`
- 允许改动：
  - `main.py`（写入 execution_request.json 的显式命令入口）
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/approval-aware-rerun-plan`
- 允许改动：
  - `main.py`（写入 rerun_plan.json 的显式命令入口）
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

### `track/controlled-execution-toggle`
- 允许改动：
  - `main.py`（--enable-mutation 诊断入口，仍然 blocked）
  - `forgeflow/runtime/**`
  - `tests/unit/runtime/**`
  - `tests/unit/entrypoints/**`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/unit/agents/**`

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

### `track/repo-metadata-mit`
- 允许改动：
  - `LICENSE`
  - `docs/**`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/**`
  - `main.py`

### `track/community-standards-v0`
- 允许改动：
  - `CODE_OF_CONDUCT.md`
  - `CODE_OF_CONDUCT.en.md`
  - `CONTRIBUTING.md`
  - `CONTRIBUTING.en.md`
  - `SECURITY.md`
  - `SECURITY.en.md`
  - `docs/branch-boundaries.md`
  - `.github/workflows/**`
  - `scripts/branch_path_guard.sh`
- 禁止改动：
  - `agents/**`
  - `tui/**`
  - `schemas/**`
  - `tests/**`
  - `main.py`

## 通用规则
- `main` 仅通过 PR 合并，不直接开发。
- CI 需通过 `ruff check .`、`pytest -q`、分支路径守卫。
- 如需跨轨道改动，请拆成多个 PR，不在单个 PR 混改。
