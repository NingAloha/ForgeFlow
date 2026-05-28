# LLM Contract

本文件定义 requirements 阶段的 LLM 输出契约。

## 1) Question Prompt Contract

输出必须为：

```json
{ "question": "..." }
```

约束：

- 只优化提问质量
- 不修改 artifact
- 不输出 `operations`
- 不输出 artifact path
- 不泄漏 features / architecture / tech stack

## 2) Typed Extraction Prompt Contract

按 sieve 返回 typed payload。例如：

```json
{ "target_users": ["..."] }
```

```json
{
  "application_type": ["..."],
  "target_platforms": ["..."],
  "detected_inconsistencies": []
}
```

```json
{
  "capability_categories": ["..."],
  "detected_inconsistencies": []
}
```

硬约束：

- 不返回 `operations`
- 不返回 artifact paths
- 不返回完整 artifact
- 不控制 `pending_clarifications`
- 不控制 `maturity`
- 不直接写完整 `Inconsistency` 系统字段

## 3) Intent Prompt Contract

intent 输出 typed payload：

```json
{
  "raw_input": "...",
  "goal": "...",
  "domain": "..."
}
```

并遵循：

- 不返回 `operations`
- 不返回 artifact paths
- 不返回完整 artifact
- 不控制 `pending_clarifications`
- 不控制 `maturity`
- 不控制 `inconsistencies`

流程字段由 Rust 固定注入。
