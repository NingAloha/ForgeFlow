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
