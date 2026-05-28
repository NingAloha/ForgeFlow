# Manual Runner

当前 `src/main.rs` 是开发期手动分发入口，不是正式 router/CLI。

## 支持命令

```bash
cargo run -- requirements intent
cargo run -- requirements target-users
cargo run -- requirements application-boundary
cargo run -- requirements capability-categories
cargo run -- requirements explicit-constraints
cargo run -- requirements non-goals
```

## 设计边界

该 runner 只做命令分发，不做：

- 自动串联 sieve
- 自动推进 next step
- blocking inconsistency gate
- end-to-end pipeline orchestration

## 对应行为

- `requirements intent`
  - 从 stdin 读取输入
  - 调用 `capture_intent`
  - 调用 `save_requirements`
  - pretty print artifact

- `requirements target-users`
  - 调用 `run_target_users_scope()`

- `requirements application-boundary`
  - 调用 `run_application_boundary_scope()`

- `requirements capability-categories`
  - 调用 `run_capability_categories_scope()`

- `requirements explicit-constraints`
  - 调用 `run_explicit_constraints_scope()`

- `requirements non-goals`
  - 调用 `run_non_goals_scope()`

## 验证命令

```bash
cargo check
cargo test -q
```
