# Implementation Execution Governance (Preview-only)

本页描述 `IMPLEMENTATION` 阶段当前的 execution governance：系统可以**解释**执行边界，但不能**跨越**执行边界。

## 当前语义（固定）
Implementation 当前只产出：
- handoff checklist（对齐 design contracts / data flow 的模块级清单）
- preview-only 元数据（当且仅当存在安全 preview 时）

Implementation 当前不做：
- 不执行 patch
- 不写用户项目文件
- 不运行 shell command
- 不开启 mutation runtime

## 状态字段
`implementation_status` 增加两个稳定字段：

### `execution_policy`
结构化描述当前执行边界：

- `mutation_enabled`: `false`
- `execution_allowed`: `false`
- `execution_mode`: `"preview-only"`
- `requires_approval`: `true`
- `blocking_reason`: `"mutation_disabled"`
- `safe_preview_available`: 等价于 `patch_preview_metadata is not None`

### `patch_preview_metadata`
当且仅当本次输出包含安全 preview 时存在，否则为 `null`：

- `generated_by`: `"ImplementationEngineerAgent"`
- `source_artifacts`: `["system_design"]`
- `preview_only`: `true`
- `target_module`: 目标模块名

## 未来扩展点
`requires_approval=true` 表示未来可能引入 approval gate 与可控执行；但当前版本仍强制：

`execution_allowed=false` 且 `mutation_enabled=false`

