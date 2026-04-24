# `DONE` Criteria

`DONE` 表示当前这一轮需求闭环已经完成。

进入条件：

* 当前主流程已经完成 `TESTING`。
* `test_report.json` 中的 `result` 已有明确结论，且结果满足当前交付要求。
* 不存在会阻止交付的开放问题，尤其是高优先级或阻塞性的 `issues`。
* orchestrator 判断当前无需继续回流到 requirements、solution、design 或 implementation。

阶段语义：

* 当前轮需求的最小闭环已经完成。
* 当前结果已满足本轮 `acceptance_criteria` 与 MVP 交付目标。
* 后续如果出现新需求或新增变更，应视为开启下一轮流程，而不是继续停留在 `DONE` 内部处理。

不能视为已进入 `DONE` 的情况：

* `test_report.result` 仍为 `not_run`、`fail` 或其他不能支持交付的状态。
* 测试中仍存在需要继续修复的关键问题。
* 虽然测试结束，但 orchestrator 已判断必须回流到上游阶段处理设计、实现或需求问题。

orchestrator 判断原则：

* `DONE` 不是“没有任何 issue”，而是“没有阻止当前轮交付的未决问题”。
* 是否进入 `DONE` 由“当前轮闭环是否完成”决定，而不是由开发活动是否暂时停止决定。
* 一旦用户提出新的明确需求，应开启下一轮流程，而不是把新需求并入当前 `DONE` 状态。
