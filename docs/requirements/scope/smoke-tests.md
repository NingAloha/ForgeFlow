# Smoke Tests

本文件记录开发期手动 smoke test 流程。

## 基础校验

```bash
cargo check
cargo test -q
```

## 用例 1：target_users shared qualifier

1. 运行 intent：

```bash
cargo run -- requirements intent
```

输入：`做一个ide`

2. 运行 target-users：

```bash
cargo run -- requirements target-users
```

输入：`有一定开发经验的，掌握工业化开发流程的学生和开发者`

预期：

- `product.target_users` 包含：
  - `有一定开发经验并掌握工业化开发流程的学生`
  - `有一定开发经验并掌握工业化开发流程的开发者`
- `pending_clarifications` 中不再包含 `product.target_users`

## 用例 2：application_type normal

```bash
cargo run -- requirements application-type
```

输入：`做 Web 应用`

预期：

- `product.application_type = ["Web 应用"]`
- `product.application_type` 对应 pending 被移除

## 用例 3：target_platforms normal

```bash
cargo run -- requirements target-platforms
```

输入：`Web`

预期：

- `product.target_platforms = ["Web"]`
- `product.target_platforms` 对应 pending 被移除

说明：

- `application_type × target_platforms` 的跨字段一致性检查属于未来 reviewer 层，不在当前 atomic sieve 中处理。

## 用例 4：capability_categories normal

```bash
cargo run -- requirements capability-categories
```

输入：`代码编辑、运行调试、版本控制集成`

预期：

- `scope.capability_categories` 被填充
- 对应 pending 被移除（仅在无 inconsistency 时）

## 用例 5：capability_categories technical-stack blocking

```bash
cargo run -- requirements capability-categories
```

输入：`用 React、PostgreSQL 和 Redis 做`

预期：

- 产生 blocking inconsistency（capability categories 语义不充分）
- `scope.capability_categories` pending 保留

## 用例 6：mandatory_constraints technical constraint

```bash
cargo run -- requirements mandatory-constraints
```

输入：`必须用 React、PostgreSQL 和 Redis`

预期：

- `scope.mandatory_constraints` 写入一条 `kind=technical` 约束
- 对应 pending 被移除
- 不产生 inconsistency

## 用例 7：mandatory_constraints no additional constraints

```bash
cargo run -- requirements mandatory-constraints
```

输入：`暂无其他约束`

预期：

- `scope.mandatory_constraints` 保持空数组
- 对应 pending 被移除
- 不产生 inconsistency

说明：

- clean “暂无其他约束” path 需要从无旧 mandatory_constraints inconsistency 的 runtime 开始。
- 若先产生 `scope.mandatory_constraints.uncertain_mandatory_constraints_absence`，再回答“暂无其他约束”，该场景验证的是未来 review/resolution 语义，而非 mandatory_constraints sieve 自身职责。

## 用例 8：mandatory_constraints repetition/vague blocking

```bash
cargo run -- requirements mandatory-constraints
```

输入示例：`还是大学生，Web 应用，支持 Web` 或 `性能要好`

预期：

- 产生 blocking inconsistency
- 对应 pending 保留
- 不将一等字段重复项当作 mandatory constraints 完成结果

## 用例 9：scope_exclusions normal

```bash
cargo run -- requirements scope-exclusions
```

输入：`不做移动端，暂不支持跨校交易`

预期：

- `scope.scope_exclusions` 写入结构化负向范围边界（每项包含 `kind` 和 `text` 字段，其中 `kind ∈ {release, deferred, permanent}`）
- 对应 pending 被移除
- 不产生 inconsistency

## 用例 10：scope_exclusions no explicit scope-exclusions

```bash
cargo run -- requirements scope-exclusions
```

输入：`暂无明确不做的范围`

预期：

- `scope.scope_exclusions` 保持空数组
- 对应 pending 被移除
- 不产生 inconsistency

## 用例 11：scope_exclusions vague/mixed blocking

```bash
cargo run -- requirements scope-exclusions
```

输入示例：`先这样`、`不做移动端` 或 `不做移动端，禁止公开学生手机号`

预期：

- 产生 blocking inconsistency
- 对应 pending 保留
- 未限定语境的“`不做 X`”可产生 `ambiguous_scope_exclusion_commitment`
- mixed answer 场景可写入有效 scope-exclusion，但不会在该轮移除 pending
