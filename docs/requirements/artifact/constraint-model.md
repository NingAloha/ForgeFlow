# Constraint Model

ForgeFlow 将 requirements capture 视为“逐步形成约束（progressive constraint formation）”的过程。

## 一等约束与额外约束

以下字段是被提升为一等字段的约束，因为它们稳定、高频、并被后续 agent 强消费：

- `product.target_users`
- `product.application_type`
- `product.target_platforms`
- `scope.capability_categories`
- `scope.scope_exclusions`

`scope.mandatory_constraints` 不是“系统内所有约束”的总容器。
它存放的是：尚未被上述一等字段表示、且由用户明确声明的额外约束。

## 字段选择规则（显式判定）

按用户回答中的语义片段判定。每个语义片段按以下顺序匹配；命中即停止，不再落到后续字段：

1. 若语义是“谁使用系统”，写入 `product.target_users`。
2. 若语义是“应用形态”（Web/App/CLI/扩展等），写入 `product.application_type`。
3. 若语义是“目标平台”（Web/iOS/Android/macOS/Windows/Linux 等），写入 `product.target_platforms`。
4. 若语义是“产品要做的能力大类”，写入 `scope.capability_categories`。
5. 若语义是“产品明确不做/暂不支持/排除在范围外”，写入 `scope.scope_exclusions`（并使用 `permanent/release/deferred`）。
6. 仅当以上字段都不适用，且语义是“必须遵守的额外规则”，才写入 `scope.mandatory_constraints`。

禁止回退规则：

- 不得把本应落在前 5 类一等边界字段的内容回退到 `scope.mandatory_constraints`。
- `scope.mandatory_constraints` 只承载补充性强制约束，不承载主边界定义。

边界反例（防误读）：

- “首版不做 X / MVP 不做 X / 暂不做 X / 后续再考虑 X / 原则上不做 X”属于 `scope.scope_exclusions`。
- policy/security/data/compliance 一类必须遵守的禁止性规则属于 `scope.mandatory_constraints`。

## 语义示例

- `target_users`：约束交互复杂度、权限、语言、能力优先级。
- `application_type`：约束交互模型、部署方式、系统集成边界。
- `target_platforms`：约束兼容性边界、技术选型空间、测试矩阵。
- `capability_categories`：约束正向能力边界。
- `capability_categories`：约束后续需求展开的正向范围，不表示单条强制规则。
- `scope_exclusions`：约束负向范围边界，并区分承诺强度：
  - `permanent`：原则上/长期不做
  - `release`：当前版本/MVP/首版不做
  - `deferred`：暂缓，后续再考虑
- `mandatory_constraints`：承载剩余的 technical/platform/policy/resource/performance/integration/data/business/other 强制约束。
- `mandatory_constraints`：其中的约束是后续阶段必须遵守的规则；不承载用户、平台、应用形态、能力范围或范围排除这些主边界。

## 为什么不把所有约束塞进一个字段

如果把用户/平台/形态全部降级到 `mandatory_constraints`，后续 agent 每次都要重新解析字符串来恢复关键边界，导致结构可用性下降。
因此采用“一等约束字段 + 额外强制约束字段”的拆分。

## 相关行为语义

本文档描述的是约束字段语义模型，不定义澄清流程执行规则。
关于 scope sieve 的 pending / inconsistency 行为矩阵，见 [Scope Behavior Matrix](../scope/behavior-matrix.md)。
