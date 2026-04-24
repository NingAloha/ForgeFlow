# `SOLUTION` Criteria

`SOLUTION` 表示方案已经足够稳定，可以进入 `DESIGN` 阶段。

必须满足：

* `selected_stack` 中与当前项目直接相关的关键技术位已经明确，尤其是核心执行层 `backend`。
* 如果项目存在明确交互层，则对应的 `frontend` 已明确；如果项目以 agent 为核心，则 `agent_framework` 已明确。
* `module_mapping` 非空，且已经列出本轮方案中的核心模块。
* 每个核心模块都具备基本职责说明，即 `module` 与 `responsibilities` 已形成稳定映射。
* 核心需求已经被模块承接，即主要 `functional_requirements` 在 `covers_requirements` 中已有归属。

建议满足：

* `database` 与 `deployment` 至少有清晰方向，且不能与当前约束冲突。
* `depends_on` 建议明确主要模块依赖关系；如果当前只是粗粒度方案，可以允许后续在 design 阶段继续细化。
* `risks` 建议记录；`alternatives` 可选；`tech_note` 只在存在模块级特殊技术偏好时填写。

不能推进的情况：

* 核心技术方案仍然悬空，导致 design 阶段无法继续展开结构设计。
* 关键需求尚未被任何模块承接，或多个模块职责明显重叠、边界混乱。
* 方案与 `spec` 中的硬约束冲突，或尚未体现用户已明确提出的技术限制。
* 方案只停留在技术名词罗列，尚未形成“技术选择 + 模块承接关系”的可设计结构。

orchestrator 判断原则：

* 不以 `selected_stack` 每个字段都非空为 ready 标准，而以“关键技术位是否足够支撑 design”为准。
* 不以 `module_mapping` 条目数量为 ready 标准，而以“核心需求是否已有稳定模块承接”为准。
* 可以对所有 `module_mapping[].covers_requirements` 取并集作为覆盖集合，用于检查核心需求是否已被承接。
* `risks` 和 `alternatives` 用于提高方案质量，但不应取代核心方案判断。
