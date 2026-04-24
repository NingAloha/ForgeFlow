# `question_state.json`

这是当前已经引入的第一类扩展状态，用于承接 agent 面向用户的结构化澄清。

它解决的问题是：

* 某阶段已经识别到信息缺口，但不能只靠自由文本追问
* orchestrator 需要知道当前是否应该暂停推进并等待用户回答
* TUI 需要知道应该展示什么问题、有哪些可选项、回答后如何回填

契约：

```json
{
  "status": "idle",
  "stage_name": "",
  "state_key": "",
  "blocking": false,
  "questions": [
    {
      "id": "",
      "title": "",
      "description": "",
      "response_type": "single_select",
      "options": [
        {
          "label": "",
          "value": "",
          "hint": ""
        }
      ],
      "allow_free_text": false,
      "answer": {
        "selected_values": [],
        "free_text": ""
      }
    }
  ],
  "created_by": "",
  "resolution_summary": ""
}
```

关键字段：

* `status`：当前使用 `idle`、`awaiting_user`、`answered`、`resolved`
* `stage_name`：发起提问的阶段
* `state_key`：本次提问主要关联的状态文件
* `blocking`：该组问题是否阻塞当前阶段继续推进
* `questions`：当前待回答的问题列表
* `questions[].answer`：当前问题的回答结果
* `created_by`：发起提问的 agent 或控制层名称
* `resolution_summary`：问题被消费、写回状态并恢复流程后的简短总结

约束：

* `question_state.json` 不替代 `spec.json` 或 `solution.json`
* 同一时刻应尽量只有一组活动问题
* `blocking = true` 且 `status = awaiting_user` 时，orchestrator 应优先停留在当前阶段或进入显式等待态
* `awaiting_user` 表示问题已发出、正在等用户回答；`answered` 表示用户已回答，控制层应把执行权重新交回对应阶段 agent
* 同阶段 agent 成功消费 `answered` 状态且没有发出新的问题时，控制层可以把 `question_state` 自动清回 `idle`
