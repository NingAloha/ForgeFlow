# ForgeFlow

[中文](./README.md) | [EN](./README_EN.md)

ForgeFlow is a Rust-based experimental project for stabilizing software requirement semantics.
The current focus is a requirements sieve architecture: progressively refining vague intent into structured artifacts with local validation.

## Status

### Done

- Rust project skeleton
- LLM JSON client
- requirements artifact schema and validator
- structured `pending_clarifications`, `inconsistencies`, and `mandatory_constraints`
- intent / target-users / application-boundary / capability-categories sieves
- manual development runner

### Not done yet

- router / CLI
- inconsistency review/resolution layer
- `mandatory_constraints` sieve
- `scope_exclusions` sieve
- end-to-end pipeline

## Quick run

```bash
cargo run -- requirements intent
cargo run -- requirements target-users
cargo run -- requirements application-boundary
cargo run -- requirements capability-categories
```

## Documentation

Requirements docs are currently Chinese-first:

- [Requirements docs map](docs/requirements/README.md)
- [Requirements artifact schema](docs/requirements/artifact/schema.md)
- [Constraint model](docs/requirements/artifact/constraint-model.md)
- [LLM contract](docs/requirements/intent/llm-contract.md)
- [Requirements sieve architecture](docs/requirements/scope/architecture.md)
- [Smoke tests](docs/requirements/scope/smoke-tests.md)
- [Manual runner](docs/requirements/runner/manual-runner.md)
