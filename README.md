# ForgeFlow

[中文](./README.md) | [EN](./README_EN.md)

ForgeFlow 是一个面向软件工程语义稳定化的 Rust 实验项目。
当前重点是 requirements sieve：将模糊需求逐步收敛为结构化 artifact，并通过本地校验保证可验证性。

## 当前状态

### 已完成

- Rust project skeleton
- LLM JSON client (`src/llm/`)
- requirements artifact schema
- requirements validator
- structured `pending_clarifications` queue
- structured `inconsistencies` queue
- structured `mandatory_constraints` model
- intent capture sieve
- `target_users` scope sieve
- `application_type` scope sieve
- `target_platforms` scope sieve
- `capability_categories` scope sieve
- `mandatory_constraints` scope sieve
- `scope_exclusions` scope sieve
- manual development runner

### 未完成

- router / CLI
- inconsistency review/resolution layer
- functional requirements generation
- design / implementation stages
- end-to-end automated pipeline

## 快速运行

```bash
cargo run -- requirements intent
cargo run -- requirements target-users
cargo run -- requirements application-type
cargo run -- requirements target-platforms
cargo run -- requirements capability-categories
cargo run -- requirements mandatory-constraints
cargo run -- requirements scope-exclusions
```

## 文档导航

- [Requirements docs map](docs/requirements/README.md)
- [Requirements artifact schema](docs/requirements/artifact/schema.md)
- [Constraint model](docs/requirements/artifact/constraint-model.md)
- [LLM contract](docs/requirements/intent/llm-contract.md)
- [Requirements sieve architecture](docs/requirements/scope/architecture.md)
- [Scope behavior matrix](docs/requirements/scope/behavior-matrix.md)
- [Smoke tests](docs/requirements/scope/smoke-tests.md)
- [Manual runner](docs/requirements/runner/manual-runner.md)
