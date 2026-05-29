# Requirements Scope 行为矩阵

## 1. 目的

本文档定义 requirements scope atomic sieves 的行为矩阵，包括：

- 有效回答
- 明确缺省声明
- 模糊回答
- 错层回答
- 空提取结果
- pending 移除条件
- inconsistency 处理
- 已知非职责范围

本文档不是 schema 规范，不是 router 设计，也不是 review/resolution 设计。

## 2. 全局规则

### 2.1 仅 typed extraction

LLM 只返回 typed extraction result；Rust 负责写入 artifact。

### 2.2 Pending clarification 语义

`pending_clarifications` 表示 initial clarification gates。移除 pending 代表该字段已达到 initial scope capture 的最小可用完成度；不代表字段 immutable。

### 2.3 完成后的补充

后续补充/修正属于 future amendment/revision layer。不要通过长期保留 initial pending clarifications 来支持未来编辑。

### 2.4 Blocking inconsistency

如果用户回答模糊、占位、回避、错层或内部冲突，所属 sieve 应：

- 保留相关 pending clarification
- 追加 structured blocking inconsistency
- 在可能时保存 artifact 状态

### 2.5 Contract violation

如果 LLM extraction 既没有可用 typed value，也没有 detected inconsistency，视为 LLM contract violation 并报错。

### 2.6 历史 inconsistencies

Scope sieves 不清理、不 resolved、不 stale、不重写历史 inconsistencies。

用户回答可能包含多个语义片段；各 sieve 只处理属于自己目标字段的片段。若同一回答中同时包含有效片段与错层/模糊片段，可写入明确部分，同时保留 pending 并追加 blocking inconsistency。

## 3. 行为矩阵

| Sieve | 目标字段 | 有效回答行为 | 明确缺省声明行为 | 模糊 / 占位回答行为 | 错层 / 放错层回答行为 | 空提取结果行为 | Pending 移除条件 |
|---|---|---|---|---|---|---|---|
| `target_users` | `product.target_users` | 写入 `product.target_users`；移除 `product.target_users` pending；设置 `maturity = "scope"` | 不适用（不能通过“无目标用户”完成） | 保留 pending；追加 blocking inconsistency（如 `product.target_users.unclear_target_users`） | 错层且无法提取有效目标用户时：保留 pending；追加 blocking inconsistency | `target_users=[]` 且 `detected_inconsistencies=[]` 视为 contract violation | `target_users` 非空且 `detected_inconsistencies` 为空 |
| `application_boundary` | `product.application_type`、`product.target_platforms` | 写入非空提取字段；按字段移除对应 pending；设置 `maturity = "scope"`；支持 partial completion | 不适用（不能通过“无应用边界”完成） | 保留 application boundary pending；追加 blocking inconsistency（如 `scope.application_boundary.unclear_application_boundary`） | 错层或冲突时：可写入已观测字段；保留 pending；追加 blocking inconsistency（如 `scope.application_boundary.cli_mobile_platform_conflict`） | `application_type=[]` 且 `target_platforms=[]` 且 `detected_inconsistencies=[]` 视为 contract violation | 仅当对应字段非空且 `detected_inconsistencies` 为空时，移除该字段 pending |
| `capability_categories` | `scope.capability_categories` | 写入 `scope.capability_categories`；移除 pending；设置 `maturity = "scope"` | 不适用（不能通过“无能力类别”完成） | 保留 pending；追加 blocking inconsistency（如 `scope.capability_categories.unclear_capability_categories`） | 错层（实现细节、类别过宽、要求推断）时：保留 pending；追加 blocking inconsistency | `capability_categories=[]` 且 `detected_inconsistencies=[]` 视为 contract violation | `capability_categories` 非空且 `detected_inconsistencies` 为空 |
| `mandatory_constraints` | `scope.mandatory_constraints` | 写入 `scope.mandatory_constraints`；移除 pending；设置 `maturity = "scope"` | 仅 `no_mandatory_constraints_declared=true` 时允许；保持空数组；移除 pending；设置 `maturity = "scope"` | 保留 pending；追加 blocking inconsistency（如 `scope.mandatory_constraints.uncertain_mandatory_constraints_absence`） | 错层（一等字段重复、功能回答、scope exclusion）时：保留 pending；追加 blocking inconsistency | `mandatory_constraints=[]` 且 `no_mandatory_constraints_declared=false` 且 `detected_inconsistencies=[]` 视为 contract violation | `mandatory_constraints` 非空且无 inconsistency；或 `no_mandatory_constraints_declared=true` 且无 inconsistency |
| `scope_exclusions` | `scope.scope_exclusions` | 写入 `scope.scope_exclusions`；移除 pending；设置 `maturity = "scope"` | 仅 `no_scope_exclusions_declared=true` 时允许；保持空数组；移除 pending；设置 `maturity = "scope"` | 保留 pending；追加 blocking inconsistency（如 `scope.scope_exclusions.uncertain_scope_exclusions_absence`） | 错层（mandatory constraint、功能回答）或承诺强度不明确时：保留 pending；追加 blocking inconsistency | `scope_exclusions=[]` 且 `no_scope_exclusions_declared=false` 且 `detected_inconsistencies=[]` 视为 contract violation | `scope_exclusions` 非空且无 inconsistency；或 `no_scope_exclusions_declared=true` 且无 inconsistency |

## 4. 各 Sieve 说明

### target_users

- Shared qualifiers 应在适用的用户组中保留与传播。
- Identity labels 不应被错误传播为 shared qualifiers。

### application_boundary

- 支持 partial completion。
- 当 inconsistency 存在时采用 write-observed-but-block-progress。
- 语义冲突检测当前主要由 prompt 驱动，不由 Rust 硬编码全量规则。

### capability_categories

- 只有用户明确给出的具体功能，才可归并为高层 capability categories。
- 不应根据常见产品知识做能力推断。

### mandatory_constraints

- 存放不被一等字段覆盖的额外强制约束。
- scope/release/deferred/permanent 的负向范围边界属于 `scope_exclusions`。

### scope_exclusions

- 区分 `release`、`deferred`、`permanent`。
- policy/security/data/compliance 类型禁止性约束属于 `mandatory_constraints`。

## 5. 非职责范围 / 未来层

当前 scope sieves 不实现：

- router scheduling
- review/resolution lifecycle
- stale/resolved inconsistency status
- amendment/revision layer
- post-completion supplements 的 append/merge 语义
- 面向所有 prompt-detected conflict 的 Rust deterministic semantic rule engine

未来层职责：

- router：根据 pending/inconsistencies/user intent 决定下一步动作
- review/resolution：判定历史 inconsistencies 是 active/resolved/stale
- amendment layer：处理 initial clarification 完成后的补充/修正

## 6. 验证清单

- `cargo check`
- `cargo test -q`
- `rg "explicit_constraints|non_goals|NonGoal|NON_GOAL|non_goal|vague_non_goal|explicit constraint|explicit constraints" src docs README.md README_EN.md examples`
