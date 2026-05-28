# ForgeFlow

[中文](./README.md) | [EN](./README_EN.md)

ForgeFlow is a Rust-based experimental project for stabilizing software requirement semantics.
Its current focus is the requirements sieve architecture: progressively refining vague user intent into a structured artifact through small, verifiable atomic sieves.

## Status

### Done

- Rust project skeleton
- LLM JSON client (`src/llm/`)
- requirements artifact schema
- requirements example template
- requirements validator
- structured `pending_clarifications` queue
- structured `inconsistencies` queue
- intent capture sieve
- `target_users` scope sieve
- `application_boundary` scope sieve
- typed extraction for scope sieves
- manual smoke-test workflow

### Not done yet

- router / CLI
- inconsistency review/resolution layer
- `capability_categories` sieve
- `constraints` sieve
- `non_goals` sieve
- functional requirements generation
- design / implementation stages
- end-to-end automated pipeline

## Current Rust Layout

```text
src/
  llm/
  mutation/
    json_read.rs
    json_write.rs
    operations.rs
  runtime/
    paths.rs
  sieves/
    requirements/
      artifact.rs
      io.rs
      validator.rs
      intent/
        capture.rs
        prompts/
          capture_system.txt
      scope/
        target_users.rs
        application_boundary.rs
        prompts/
          target_users_question_system.txt
          target_users_extract_system.txt
          application_boundary_question_system.txt
          application_boundary_extract_system.txt
examples/
  sieves/
    requirements/
      requirements.example.json
.runtime/
  sieves/
    requirements/
      requirements.json
```

Note: router/CLI is not implemented yet. Development currently runs one sieve at a time by temporarily switching `main.rs`.

## Requirements Artifact Schema

```json
{
  "artifact_type": "requirements",
  "schema_version": "0.1",
  "maturity": "intent | scope | capability | requirement | review_ready",
  "intent": {
    "raw_input": "",
    "goal": "",
    "domain": ""
  },
  "product": {
    "target_users": [],
    "application_type": [],
    "target_platforms": []
  },
  "scope": {
    "capability_categories": [],
    "constraints": [],
    "non_goals": []
  },
  "functional_requirements": [],
  "non_functional_requirements": [],
  "external_interfaces": [],
  "data_requirements": [],
  "pending_clarifications": [],
  "inconsistencies": []
}
```

### `pending_clarifications`

Example:

```json
{
  "id": "product.target_users",
  "target_path": ["product", "target_users"],
  "question": "目标用户是谁？",
  "sieve": "requirements.scope.target_users"
}
```

Rules:

- `id == target_path.join(".")`
- Present in queue means unresolved
- Removed from queue means handled by the corresponding sieve
- No `status`
- No history log

### `inconsistencies`

Example:

```json
{
  "id": "scope.application_boundary.cli_mobile_platform_conflict",
  "stage": "scope",
  "sieve": "requirements.scope.application_boundary",
  "severity": "blocking",
  "target_paths": [
    ["product", "application_type"],
    ["product", "target_platforms"]
  ],
  "message": "CLI 工具通常不以 iOS/Android 作为直接运行平台，需要进一步澄清目标运行环境。",
  "requires_clarification": true
}
```

Rules:

- `severity` is currently limited to `blocking` or `warning`
- Present in queue means unresolved
- Removed means resolved
- No `status`
- No `resolution_log`
- With any `blocking` inconsistency, the next stage should not proceed (future review layer)

## Requirements Sieve Architecture

### 1) Intent capture

Responsibilities:

- User provides raw idea
- LLM only normalizes:
  - `intent.raw_input`
  - `intent.goal`
  - `intent.domain`
- Rust sets fixed process fields:
  - `maturity = "intent"`
  - fixed scope-v0 `pending_clarifications` list

Fixed six clarifications:

- `product.target_users -> requirements.scope.target_users`
- `product.application_type -> requirements.scope.application_boundary`
- `product.target_platforms -> requirements.scope.application_boundary`
- `scope.capability_categories -> requirements.scope.capability_categories`
- `scope.constraints -> requirements.scope.constraints`
- `scope.non_goals -> requirements.scope.non_goals`

### 2) `target_users` scope sieve

Responsibilities:

- Question LLM generates a contextual follow-up question
- Extraction LLM returns typed result:

```json
{
  "target_users": ["..."]
}
```

- Rust writes `product.target_users`
- Rust removes `pending_clarifications[id == "product.target_users"]`
- Rust sets `maturity = "scope"`

Notes:

- Scope extraction LLM is not `OperationSet`
- LLM does not control artifact paths
- Shared qualifier rule is preserved:
  - Input: `有一定开发经验的，掌握工业化开发流程的学生和开发者`
  - Output must keep qualifiers on both groups

### 3) `application_boundary` scope sieve

Responsibilities:

- Handles both:
  - `product.application_type`
  - `product.target_platforms`
- Question LLM generates contextual clarification
- Extraction LLM returns typed result:

```json
{
  "application_type": ["桌面应用"],
  "target_platforms": ["macOS"],
  "detected_inconsistencies": []
}
```

- Rust writes extracted fields
- Rust removes only the pending items corresponding to fields actually updated
- Rust converts `detected_inconsistencies` into structured `Inconsistency`
- Converted inconsistency severity is fixed to `blocking`

Partial completion examples:

- `先做桌面端` -> `application_type=["桌面应用"]`, `target_platforms=[]`
- `支持 Windows 和 macOS` -> `application_type=[]`, `target_platforms=["Windows", "macOS"]`
- `做 Web 应用` -> `application_type=["Web 应用"]`, `target_platforms=["Web"]`
- `做 CLI 工具，支持 iOS 和 Android` -> fields updated + blocking inconsistency appended

## LLM Contract

### Question prompts

Must return only:

```json
{
  "question": "..."
}
```

Rules:

- Improve question quality only
- Never mutate artifact
- Never output `operations`
- Do not enumerate candidate answers unless explicitly present in the original user intent
- No feature/architecture/tech-stack leakage

### Typed extraction prompts

Must return sieve-specific typed payload, for example:

```json
{
  "target_users": ["..."]
}
```

or:

```json
{
  "application_type": ["..."],
  "target_platforms": ["..."],
  "detected_inconsistencies": []
}
```

Rules:

- No artifact paths
- No `operations`
- No full artifact
- No control of `pending_clarifications`
- No control of `maturity`
- No direct full `Inconsistency` system fields

### Intent prompt

Intent currently remains operation-limited, but allowed paths are only:

- `intent.raw_input`
- `intent.goal`
- `intent.domain`

Rust injects process fields.

### About `mutation::operations`

`mutation::operations` is now closer to an internal primitive / legacy support layer, not the recommended LLM-facing contract for new scope sieves.

## Manual Development Entrypoints

No formal router/CLI yet. During development, switch `src/main.rs` to run one sieve.

### Intent

```rust
fn main() -> anyhow::Result<()> {
    use std::io::{self, Write};
    print!("Requirement> ");
    io::stdout().flush()?;
    let mut user_input = String::new();
    io::stdin().read_line(&mut user_input)?;
    let artifact = sieves::requirements::intent::capture::capture_intent(user_input.trim())?;
    sieves::requirements::io::save_requirements(&artifact)?;
    println!("{}", serde_json::to_string_pretty(&artifact)?);
    Ok(())
}
```

### Target users

```rust
fn main() -> anyhow::Result<()> {
    sieves::requirements::scope::target_users::run_target_users_scope()
}
```

### Application boundary

```rust
fn main() -> anyhow::Result<()> {
    sieves::requirements::scope::application_boundary::run_application_boundary_scope()
}
```

Commands:

```bash
cargo check
cargo test -q
cargo run
```

## Manual Smoke Tests

### 1) `target_users` shared qualifier

1. Run intent with input: `做一个ide`
2. Run target_users with input: `有一定开发经验的，掌握工业化开发流程的学生和开发者`

Expected:

```json
"target_users": [
  "有一定开发经验并掌握工业化开发流程的学生",
  "有一定开发经验并掌握工业化开发流程的开发者"
]
```

And `pending_clarifications` should no longer contain `product.target_users`.

### 2) `application_boundary` Web compound

Input: `做 Web 应用`

Expected:

```json
"application_type": ["Web 应用"],
"target_platforms": ["Web"]
```

### 3) `application_boundary` inconsistency

Input: `做 CLI 工具，支持 iOS 和 Android`

Expected:

```json
"inconsistencies": [
  {
    "id": "scope.application_boundary.cli_mobile_platform_conflict",
    "stage": "scope",
    "sieve": "requirements.scope.application_boundary",
    "severity": "blocking",
    "requires_clarification": true
  }
]
```

## Stale Design Replacements

This README now replaces old references such as:

- `open_questions` -> `pending_clarifications`
- Python module paths (`sieves/requirements/*.py`, `llm/api.py`) -> Rust module paths
- LLM full-artifact generation -> typed extraction + Rust mutation authority
- Scope `OperationSet` contract -> scope typed extraction contract
- `sieves/requirements/requirements.example.json` -> `examples/sieves/requirements/requirements.example.json`
- `.runtime/requirements/requirements.json` -> `.runtime/sieves/requirements/requirements.json`
