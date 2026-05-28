# Requirements Artifact Schema

本文件是 requirements artifact 的结构性说明（schema source of truth）。

## 顶层结构

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
    "mandatory_constraints": [],
    "scope_exclusions": []
  },
  "functional_requirements": [],
  "non_functional_requirements": [],
  "external_interfaces": [],
  "data_requirements": [],
  "pending_clarifications": [],
  "inconsistencies": []
}
```

## Product

- `product.target_users: string[]`
- `product.application_type: string[]`
- `product.target_platforms: string[]`

## Scope

- `scope.capability_categories: string[]`
- `scope.mandatory_constraints: Constraint[]`
- `scope.scope_exclusions: ScopeExclusion[]`

### Constraint

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
- `other`

说明：`examples/sieves/requirements/requirements.example.json` 保持空模板，即：

```json
"mandatory_constraints": []
```

### ScopeExclusion

```json
{
  "kind": "release",
  "text": "首版不开发移动端应用"
}
```

允许的 `kind`：

- `permanent`
- `release`
- `deferred`

## Pending Clarification

```json
{
  "id": "scope.mandatory_constraints",
  "target_path": ["scope", "mandatory_constraints"],
  "question": "是否有其他明确约束？",
  "sieve": "requirements.scope.mandatory_constraints"
}
```

规则：

- `id == target_path.join(".")`
- 仍存在于 `pending_clarifications` 表示未完成
- 被移除表示对应 sieve 已完成该字段

## Inconsistency

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

- `severity` 只允许 `blocking` 或 `warning`
- 存在于 `inconsistencies` 表示问题未解决
- 被移除表示问题已解决
- 当前不使用 `status` 与 `resolution_log`
