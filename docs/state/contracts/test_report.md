# `test_report.json`

用于保存验证阶段状态，回答“测了什么、结果如何、问题归因到哪里”。

```json
{
  "test_scope": "",
  "result": "not_run",
  "issues": []
}
```

关键字段：

* `test_scope`：本轮验证范围
* `result`：例如 `not_run`、`partial`、`fail`、`pass`
* `issues`：验证阶段发现的问题列表
* `issues[].severity`：问题严重级别
* `issues[].status`：问题当前状态
* `issues[].related_modules`：归因模块
* `issues[].related_contracts`：归因 contract
* `issues[].notes`：补充说明

结果语义：

* `not_run`：测试尚未真正执行
* `partial`：执行了部分验证，但归因仍不完整
* `fail`：存在 `high/critical` 且状态为 `open/confirmed` 的问题
* `pass`：未发现阻塞交付的问题
