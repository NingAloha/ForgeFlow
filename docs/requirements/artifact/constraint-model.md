# Constraint Model

ForgeFlow 将 requirements capture 视为“逐步形成约束（progressive constraint formation）”的过程。

## 一等约束与额外约束

以下字段是被提升为一等字段的约束，因为它们稳定、高频、并被后续 agent 强消费：

- `product.target_users`
- `product.application_type`
- `product.target_platforms`
- `scope.capability_categories`
- `scope.non_goals`

`scope.explicit_constraints` 不是“系统内所有约束”的总容器。
它存放的是：尚未被上述一等字段表示、且由用户明确声明的额外约束。

## 语义示例

- `target_users`：约束交互复杂度、权限、语言、能力优先级。
- `application_type`：约束交互模型、部署方式、系统集成边界。
- `target_platforms`：约束兼容性边界、技术选型空间、测试矩阵。
- `capability_categories`：约束正向能力边界。
- `non_goals`：约束负向范围边界，并区分承诺强度：
  - `permanent`：原则上/长期不做
  - `release`：当前版本/MVP/首版不做
  - `deferred`：暂缓，后续再考虑
- `explicit_constraints`：承载剩余的 technical/platform/policy/resource/performance/integration/data/business/scope 约束。

## 为什么不把所有约束塞进一个字段

如果把用户/平台/形态全部降级到 `explicit_constraints`，后续 agent 每次都要重新解析字符串来恢复关键边界，导致结构可用性下降。
因此采用“一等约束字段 + 额外显式约束字段”的拆分。
