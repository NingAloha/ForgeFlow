# `implementation_status.json`

用于保存实现阶段状态，回答“当前正在实现什么，做到哪里，卡在哪里”。

```json
{
  "module_name": "",
  "implementation_status": "not_started",
  "files_touched": [],
  "tests_added_or_updated": [],
  "contract_compliance": true,
  "known_limitations": [],
  "blockers": []
}
```

关键字段：

* `module_name`：当前正在实现的模块
* `implementation_status`：如 `not_started`、`in_progress`、`blocked`、`done`
* `files_touched`：已触达文件
* `tests_added_or_updated`：新增或更新的测试
* `contract_compliance`：当前实现是否满足既有 contract
* `known_limitations`：当前已知限制
* `blockers`：阻塞当前实现继续推进的问题
