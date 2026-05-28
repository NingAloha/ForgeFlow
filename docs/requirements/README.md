# Requirements Docs Map

本目录按 `src/sieves/requirements` 的模块边界组织。

- `artifact/`
  - 对应 `src/sieves/requirements/artifact.rs`
  - [schema](./artifact/schema.md)
  - [constraint model](./artifact/constraint-model.md)
- `intent/`
  - 对应 `src/sieves/requirements/intent/*`
  - [llm contract](./intent/llm-contract.md)
- `scope/`
  - 对应 `src/sieves/requirements/scope/*`
  - [architecture](./scope/architecture.md)
  - [smoke tests](./scope/smoke-tests.md)
- `runner/`
  - 对应 `src/main.rs`（manual dev runner）
  - [manual runner](./runner/manual-runner.md)
