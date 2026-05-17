# 贡献指南（Contributing）

English: `CONTRIBUTING.en.md`

## 当前 ForgeFlow 是什么

ForgeFlow is a structured AI workflow runtime. ForgeFlow SE is its first target profile.

ForgeFlow Runtime v0 已稳定 control-plane 语义；execution engine 刻意缺席（mutation disabled by design）。

## 开发工作流

安装（editable）：

```bash
python3.11 -m pip install -e ".[dev]"
```

常用命令：

```bash
python3.11 main.py --auto-run "<requirement>"
python3.11 main.py --status
python3.11 main.py --replay --run-id <run_id>
```

## 分支契约模型

- `main` 只通过 PR 更新。
- `track/*` 是主要开发模型：一个分支 = 一个 runtime contract。
- PR scope 保持小且明确；不要混入不相关的 contract。
- 分支允许改动范围由 CI 强制；见 `docs/branch-boundaries.md`。

## 质量检查

在开 PR 前本地运行：

```bash
ruff check .
pytest -q
```

## PR 期望

- 使用 contract-centric 标题（例如 `docs: ...`, `runtime: ...`, `ci: ...`）。
- 写清本次引入/强化的不变量（invariants）。
- 行为变化必须配套 tests；docs 变化必须保持 vocabulary 稳定。
- 不得模糊 truth artifacts 与 intent artifacts 的边界。
- 合并后删除分支。

## 当前 runtime 边界（v0）

- Truth artifacts：`summary.json`, `events.jsonl`, `lineage.json`, `review_state.json`, `approvals/*.json`。
- Intent artifacts：`execution_request.json`, `rerun_plan.json`（intent ≠ factual truth）。
- `--enable-mutation` 只是 gate diagnostics（blocked / not implemented）。
- Mutation disabled by design：v0 PR 不得引入 workspace mutation。
