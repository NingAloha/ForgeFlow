# Stage Model

当前实现采用一组布尔链作为阶段真相来源：

* `requirements_ready`
* `solution_ready`
* `design_ready`
* `implementing_active`
* `testing_active`
* `done_ready`

这些布尔值按顺序依赖，前一层不成立，后一层原则上也不应成立。

当前真相阶段取“最后一个成立的布尔值对应阶段”。

这意味着：

* orchestrator 的 `computed_stage` 表示当前状态文件在严格判定下还能站到哪一层。
* 阶段真相来自规则计算，而不是来自单独维护的阶段字段。
* 当上游前提失效时，阶段会自然沿链路下坠。

`source_stage` 与 `computed_stage` 不同：

* `computed_stage` 代表严格 ready / active 判定下当前还能成立到哪一层。
* `source_stage` 用于回流判断，当上游前提已经失效时，仍可根据下游产物痕迹推断“问题原本是在哪一层暴露的”。

当前 `source_stage` 推断顺序：

* 有 testing 结果或 testing issue，优先视为 `TESTING`
* 否则如果 `implementation_status` 已进入活动状态，则视为 `IMPLEMENTATION`
* 否则如果已有 design 结构、contract、data flow 或 MVP 交付定义，则视为 `DESIGN`
* 否则如果已有 solution 技术主干或模块映射，则视为 `SOLUTION`
