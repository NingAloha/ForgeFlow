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

## 用例 2：application_boundary Web compound

```bash
cargo run -- requirements application-boundary
```

输入：`做 Web 应用`

预期：

- `product.application_type = ["Web 应用"]`
- `product.target_platforms = ["Web"]`

## 用例 3：application_boundary inconsistency

```bash
cargo run -- requirements application-boundary
```

输入：`做 CLI 工具，支持 iOS 和 Android`

预期：

- 写入 `application_type` / `target_platforms`
- `inconsistencies` 新增 `scope.application_boundary.cli_mobile_platform_conflict`
- `severity = "blocking"`

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

## 用例 6：explicit_constraints technical constraint

```bash
cargo run -- requirements explicit-constraints
```

输入：`必须用 React、PostgreSQL 和 Redis`

预期：

- `scope.explicit_constraints` 写入一条 `kind=technical` 约束
- 对应 pending 被移除
- 不产生 inconsistency

## 用例 7：explicit_constraints no additional constraints

```bash
cargo run -- requirements explicit-constraints
```

输入：`暂无其他约束`

预期：

- `scope.explicit_constraints` 保持空数组
- 对应 pending 被移除
- 不产生 inconsistency

说明：

- clean “暂无其他约束” path 需要从无旧 explicit_constraints inconsistency 的 runtime 开始。
- 若先产生 `scope.explicit_constraints.uncertain_explicit_constraints_absence`，再回答“暂无其他约束”，该场景验证的是未来 review/resolution 语义，而非 explicit_constraints sieve 自身职责。

## 用例 8：explicit_constraints repetition/vague blocking

```bash
cargo run -- requirements explicit-constraints
```

输入示例：`还是大学生，Web 应用，支持 Web` 或 `性能要好`

预期：

- 产生 blocking inconsistency
- 对应 pending 保留
- 不将一等字段重复项当作 explicit constraints 完成结果
