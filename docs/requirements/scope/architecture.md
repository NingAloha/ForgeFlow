# Requirements Sieve Architecture

## 当前代码层级（与 `src/` 对齐）

```text
src/
  llm/
    mod.rs
    client.rs
  mutation/
    mod.rs
    json_read.rs
    json_write.rs
    operations.rs
  runtime/
    mod.rs
    paths.rs
  sieves/
    mod.rs
    requirements/
      mod.rs
      artifact.rs
      io.rs
      validator.rs
      intent/
        mod.rs
        capture.rs
        prompts/
          capture_system.txt
      scope/
        mod.rs
        target_users.rs
        application_boundary.rs
        capability_categories.rs
        mandatory_constraints.rs
        scope_exclusions.rs
        prompts/
          target_users_question_system.txt
          target_users_extract_system.txt
          application_boundary_question_system.txt
          application_boundary_extract_system.txt
          capability_categories_question_system.txt
          capability_categories_extract_system.txt
          mandatory_constraints_question_system.txt
          mandatory_constraints_extract_system.txt
          scope_exclusions_question_system.txt
          scope_exclusions_extract_system.txt
```

## 设计原则

- 每个 sieve 原子化、可单独运行、可单独验证。
- Question LLM 只生成澄清问题。
- Extraction LLM 只返回 typed extraction result。
- Rust 是 artifact mutation authority。
- 全部原子 sieve 稳定后，再接 router/CLI。

核心链路：

```text
Question LLM -> Typed Extraction LLM -> Rust mutation authority
```

## 当前层次

### 1. Intent capture

- 输入：用户原始意图
- LLM：只允许 `intent.raw_input / intent.goal / intent.domain`
- Rust 固定注入：
  - `maturity = "intent"`
  - scope v0 的 `pending_clarifications`

### 2. `requirements.scope.target_users`

- question prompt 生成上下文化问题
- extraction prompt 返回：

```json
{ "target_users": ["..."] }
```

- Rust 写入 `product.target_users`
- Rust 移除对应 pending
- Rust 设置 `maturity = "scope"`

### 3. `requirements.scope.application_boundary`

- 同时处理：
  - `product.application_type`
  - `product.target_platforms`
- extraction prompt 返回：

```json
{
  "application_type": ["..."],
  "target_platforms": ["..."],
  "detected_inconsistencies": []
}
```

- Rust 写入 `product.application_type` / `product.target_platforms`
- `detected_inconsistencies` 为空时，移除对应 pending
- `detected_inconsistencies` 非空时，保留对应 pending，并转换追加 blocking inconsistency

### 4. `requirements.scope.capability_categories`

- extraction prompt 返回：

```json
{
  "capability_categories": ["..."],
  "detected_inconsistencies": []
}
```

- Rust 写字段
- 若有 blocking inconsistency，则 pending 保留

### 5. `requirements.scope.mandatory_constraints`

- extraction prompt 返回：

```json
{
  "mandatory_constraints": [
    {
      "kind": "technical",
      "text": "必须使用 React、PostgreSQL 和 Redis"
    }
  ],
  "no_mandatory_constraints_declared": false,
  "detected_inconsistencies": []
}
```

- 技术栈约束在该字段合法。
- “暂无其他约束”是有效完成回答（`no_mandatory_constraints_declared=true`）。
- 重复一等字段（users/type/platform/capability/scope-exclusions）不应作为 mandatory constraints 完成结果。
- 若存在 `detected_inconsistencies`，保持 pending，不视为完成。

### 6. `requirements.scope.scope_exclusions`

- extraction prompt 返回：

```json
{
  "scope_exclusions": [
    {
      "kind": "release",
      "text": "首版不开发移动端应用"
    }
  ],
  "no_scope_exclusions_declared": false,
  "detected_inconsistencies": []
}
```

- `scope.scope_exclusions` 记录产品负向范围边界（明确不做/暂不支持/首版排除）。
- `scope_exclusions.kind` 表示承诺强度：`permanent` / `release` / `deferred`。
- 禁止性 policy/security/data/compliance 约束不应落在 `scope_exclusions`，应归入 `mandatory_constraints`。
- “暂无明确不做的范围”仅在明确声明时视为有效完成（`no_scope_exclusions_declared=true`）。
- 对未给上下文限定的“`不做 X`”，可产出 `ambiguous_scope_exclusion_commitment` 并继续澄清。
- “先这样/不确定”等不明确缺省回答应产出 blocking inconsistency 并保留 pending。
- mixed answer（有效 scope-exclusion + misplaced mandatory constraint）会写入有效 scope-exclusion，但因 inconsistency 非空仍保留 pending。

### 7. 未来层（未实现）

- review/inconsistency layer
- router/CLI

### 8. Scope sieve 与 inconsistency review/resolution 的职责边界

Scope sieve responsibilities（may）：

- 生成面向用户的澄清问题
- 从当前用户回答提取 typed result
- 修改自己负责的目标 artifact 字段
- 基于当前提取结果新增 inconsistency
- 基于当前提取结果移除或保留本 sieve 的 pending clarification

Scope sieve non-responsibilities（must not）：

- 清理历史 inconsistency
- 判定历史 inconsistency 是否已 resolved
- 实现 review 或 resolution 逻辑
- 将后续一次成功澄清视为此前 blocking inconsistency 的隐式 resolution

Historical inconsistency handling 属于未来 inconsistency review/resolution layer。该层负责：

- 检查当前 artifact state
- 检查 active blocking inconsistencies
- 判定 inconsistency 仍有效、已 resolved、或已 stale
- 当 unresolved blocking inconsistency 存在时阻止流程推进
- 在 schema 支持时记录 resolution 语义

## 当前不做

- 不自动串联 sieve
- 不自动判断 next step
- 不做 end-to-end pipeline
