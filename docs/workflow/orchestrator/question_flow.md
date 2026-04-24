# Question Flow

当前实现对 `question_state` 的处理约定是：

* `status = awaiting_user` 且 `blocking = true` 时，orchestrator 进入等待态，不执行阶段 agent。
* `status = answered` 时，不再视为“继续等待用户”；orchestrator 应恢复对应阶段的执行，让该阶段 agent 消费答案。
* 如果该阶段 agent 成功消费答案且没有重新发出问题，控制层会把 `question_state` 清回 `idle`。

这意味着：

* `awaiting_user` 表示“控制层应暂停”
* `answered` 表示“用户输入已到位，下一步应回到对应阶段继续推进”

配套阅读：

* [../../state/contracts/question_state.md](../../state/contracts/question_state.md)
* [../README.md](../README.md)
