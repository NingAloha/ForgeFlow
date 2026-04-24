# `TESTING` Criteria

`TESTING` 表示主流程已经从实现转入验证阶段。

进入条件：

* 当前这一轮实现已完成，即 `implementation_status` 已到达 `done`。
* 当前不存在会阻塞验证开始的实现级 `blockers`。
* 已有可验证对象，例如本轮实现涉及的模块、模块协作关系、关键 contracts、主流程 data flow、功能闭环或测试项已经明确。
* orchestrator 已将当前主角色切换为 `Test & Validation Engineer`。

阶段语义：

* `test_report.json` 成为当前验证阶段的主状态载体。
* `result = not_run` 表示已经进入 testing 阶段，但验证尚未真正执行完毕。
* `issues` 用于记录测试失败、异常现象以及模块级、契约级或数据流级归因结果。

不能视为已进入 `TESTING` 的情况：

* 实现仍处于 `not_started`、`in_progress` 或 `blocked`。
* 当前仍存在明显实现阻塞。
* 尚未明确本轮要验证的对象、协作边界、关键 contract 或验证范围。

orchestrator 判断原则：

* 进入 `TESTING` 的前提是“当前轮实现已经可被验证”，而不是“测试文件已经存在”。
* `IMPLEMENTATION` 的完成与 `TESTING` 的开始是相邻关系。
* testing 阶段的核心任务不是继续实现，而是验证结果、检查模块交互、contract 与 data flow 是否成立、记录问题并决定是否回流。
