# `IMPLEMENTATION` Criteria

`IMPLEMENTATION` 表示主流程已经正式进入按设计落地实现的阶段。

进入条件：

* `DESIGN` 已成立。
* 当前选定角色已切换为 `Implementation Engineer`。
* `implementation_status.json` 中的 `module_name` 已明确。
* `implementation_status` 已进入活动状态，而非 `not_started`。

阶段语义：

* `in_progress` 表示当前正在按 design 落地实现。
* `blocked` 表示当前仍属于实现阶段，但因为阻塞条件尚未解除而无法继续推进。
* `done` 表示当前这轮实现已经完成，主流程可以准备进入 testing 判定。

不能视为已进入 `IMPLEMENTATION` 的情况：

* design 尚未 ready，但已经试图直接开始编码。
* 当前没有明确实现对象。
* 仍停留在 `not_started`。

orchestrator 判断原则：

* 是否进入 `IMPLEMENTATION` 由“实现动作是否正式开始”决定，不由 `files_touched` 数量决定。
* `in_progress` 与 `blocked` 都属于实现中的活动状态。
* `done` 只表示实现阶段当前轮次完成，不自动等于整个流程结束。
