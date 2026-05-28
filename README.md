# ForgeFlow

[中文](./README.md) | [EN](./README_EN.md)

ForgeFlow 是一个面向软件工程语义稳定化的 Rust 实验项目。
当前重点是 requirements sieve：把模糊用户需求通过原子筛子逐步澄清为结构化 artifact，并在本地做结构校验。

## 当前状态

### 已完成

- Rust project skeleton
- LLM JSON client (`src/llm/`)
- requirements artifact schema
- requirements example template
- requirements validator
- `pending_clarifications` structured queue
- `inconsistencies` structured queue
- intent capture sieve
- `target_users` scope sieve
- `application_boundary` scope sieve
- typed extraction for scope sieves
- manual smoke-test workflow

### 未完成

- router / CLI
- inconsistency review/resolution layer
- `capability_categories` sieve
- `explicit_constraints` sieve
- `non_goals` sieve
- functional requirements generation
- design / implementation stages
- end-to-end automated pipeline

## 当前目录结构（Rust）

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

说明：router/CLI 尚未接入；当前通过临时 `main.rs` 运行单个 sieve。

## Requirements Artifact Schema

当前 `RequirementsArtifact` 核心结构：

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
    "explicit_constraints": [
      {
        "kind": "technical",
        "text": "必须使用 PostgreSQL"
      }
    ],
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

结构示例：

```json
{
  "id": "product.target_users",
  "target_path": ["product", "target_users"],
  "question": "目标用户是谁？",
  "sieve": "requirements.scope.target_users"
}
```

规则：

- `id == target_path.join(".")`
- 存在于 `pending_clarifications` 表示仍待处理
- 被移除表示已由对应 sieve 处理
- 不使用 `status`
- 不保存历史日志

### `inconsistencies`

结构示例：

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

规则：

- `severity` 只允许 `"blocking"` 或 `"warning"`
- 存在于 `inconsistencies` 表示当前仍未解决
- 被移除表示已解决
- 不使用 `status`
- 不使用 `resolution_log`
- 存在 `blocking` inconsistency 时，不应推进到下一阶段（后续由 review layer 负责）

### `explicit_constraints`

`scope.explicit_constraints` 现在是 typed list，而不是 string list。结构：

```json
{
  "kind": "technical",
  "text": "必须使用 PostgreSQL"
}
```

允许的 `kind`：

- `technical`
- `platform`
- `policy`
- `resource`
- `performance`
- `integration`
- `data`
- `business`
- `scope`
- `other`

说明：`examples/sieves/requirements/requirements.example.json` 仍保持 `"explicit_constraints": []`，因为它是空模板。

## Requirements Sieve Architecture

### 1. Intent Capture

职责：

- 输入用户 raw idea
- LLM 仅归一化三个字段：
  - `intent.raw_input`
  - `intent.goal`
  - `intent.domain`
- Rust 固定注入：
  - `maturity = "intent"`
  - `pending_clarifications =` scope v0 固定六项

固定六项：

- `product.target_users -> requirements.scope.target_users`
- `product.application_type -> requirements.scope.application_boundary`
- `product.target_platforms -> requirements.scope.application_boundary`
- `scope.capability_categories -> requirements.scope.capability_categories`
- `scope.explicit_constraints -> requirements.scope.explicit_constraints`
- `scope.non_goals -> requirements.scope.non_goals`

边界：

- LLM 不控制 `pending_clarifications`
- LLM 不控制 `maturity`
- LLM 不填 `product/scope/requirements` 主体字段

### 2. `target_users` Scope Sieve

职责：

- question LLM 仅生成上下文化追问
- extraction LLM 返回 typed result：

```json
{
  "target_users": ["..."]
}
```

- Rust 写入 `product.target_users`
- Rust 移除 `pending_clarifications[id == "product.target_users"]`
- Rust 设置 `maturity = "scope"`

说明：

- extraction LLM 不返回 `OperationSet`
- extraction LLM 不返回 artifact path
- 共同限定词规则：
  - 输入：`有一定开发经验的，掌握工业化开发流程的学生和开发者`
  - 输出：
    - `有一定开发经验并掌握工业化开发流程的学生`
    - `有一定开发经验并掌握工业化开发流程的开发者`

### 3. `application_boundary` Scope Sieve

职责：

- 同时处理：
  - `product.application_type`
  - `product.target_platforms`
- question LLM 仅生成上下文化追问
- extraction LLM 返回 typed result：

```json
{
  "application_type": ["桌面应用"],
  "target_platforms": ["macOS"],
  "detected_inconsistencies": []
}
```

- Rust 写入目标字段
- Rust 仅移除“本次成功写入字段”对应的 pending clarification
- Rust 将 `detected_inconsistencies` 转换为结构化 `Inconsistency`
- inconsistency `severity` 固定为 `"blocking"`

partial completion 示例：

- `先做桌面端` -> `application_type = ["桌面应用"]`, `target_platforms = []`
- `支持 Windows 和 macOS` -> `application_type = []`, `target_platforms = ["Windows", "macOS"]`
- `做 Web 应用` -> `application_type = ["Web 应用"]`, `target_platforms = ["Web"]`
- `做 CLI 工具，支持 iOS 和 Android` -> 写入字段，并记录 blocking inconsistency

## LLM Contract

### Question Prompt

输出固定为：

```json
{
  "question": "..."
}
```

约束：

- 只提升追问质量
- 不修改 artifact
- 不输出 `operations`
- 不列举具体候选答案（除非用户原始 intent 明确提到）
- 不泄漏 feature/architecture/tech stack

### Typed Extraction Prompt

输出 sieve 专属 typed result，例如：

```json
{
  "target_users": ["..."]
}
```

或：

```json
{
  "application_type": ["..."],
  "target_platforms": ["..."],
  "detected_inconsistencies": []
}
```

约束：

- 不返回 artifact path
- 不返回 `operations`
- 不返回完整 artifact
- 不控制 `pending_clarifications`
- 不控制 `maturity`
- 不直接写完整 `Inconsistency` 系统字段

### Intent Prompt

intent 当前仍使用 operation-limited 形式，但只允许三条路径：

- `intent.raw_input`
- `intent.goal`
- `intent.domain`

流程字段由 Rust 固定注入。

### 关于 `mutation::operations`

`mutation::operations` 目前更接近内部 mutation primitive / legacy support。
它不再是新 scope sieve 的 LLM-facing contract。

## Manual Development Entrypoints

当前没有正式 router/CLI。
开发阶段通过临时修改 `src/main.rs` 运行单个 sieve。

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

### Target Users

```rust
fn main() -> anyhow::Result<()> {
    sieves::requirements::scope::target_users::run_target_users_scope()
}
```

### Application Boundary

```rust
fn main() -> anyhow::Result<()> {
    sieves::requirements::scope::application_boundary::run_application_boundary_scope()
}
```

常用命令：

```bash
cargo check
cargo test -q
cargo run
```

## Manual Smoke Tests

### 1. target_users shared qualifier test

流程：

1. 跑 intent，输入：`做一个ide`
2. 跑 target_users，输入：`有一定开发经验的，掌握工业化开发流程的学生和开发者`

预期：

```json
"target_users": [
  "有一定开发经验并掌握工业化开发流程的学生",
  "有一定开发经验并掌握工业化开发流程的开发者"
]
```

并且 `pending_clarifications` 中不再包含 `product.target_users`。

### 2. application_boundary Web compound test

输入：`做 Web 应用`

预期：

```json
"application_type": ["Web 应用"],
"target_platforms": ["Web"]
```

### 3. application_boundary inconsistency test

输入：`做 CLI 工具，支持 iOS 和 Android`

预期：

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

## 过时设计替换说明

当前文档已移除/替换以下旧说法：

- `open_questions` -> `pending_clarifications`
- 旧 Python 模块路径（如 `sieves/requirements/*.py`, `llm/api.py`）-> Rust 模块路径
- “LLM 直接生成完整 requirements JSON” -> typed extraction + Rust mutation authority
- “scope extraction 返回 OperationSet” -> scope typed extraction
- `sieves/requirements/requirements.example.json` -> `examples/sieves/requirements/requirements.example.json`
- `.runtime/requirements/requirements.json` -> `.runtime/sieves/requirements/requirements.json`
