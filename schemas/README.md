# Schemas Module

这个目录存放状态契约的运行时 schema 定义（Pydantic）。

当前仓库会在 `StateManager` 的读写路径上对以下状态做结构校验：

* `spec.py`
* `solution.py`
* `design.py`
* `implementation.py`
* `testing.py`
* `question_state.py`

参考来源：

* [../docs/state/contracts.md](../docs/state/contracts.md)
* [../docs/workflow/README.md](../docs/workflow/README.md)
