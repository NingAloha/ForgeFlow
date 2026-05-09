# State Module

这个目录放项目的状态契约示例文件和字段参考。

当前文件：

* `spec.json`
* `solution.json`
* `system_design.json`
* `implementation_status.json`
* `test_report.json`
* `question_state.json`

这些文件描述最小持久化契约，并作为默认状态结构参考。

当前默认约定：

* 空列表表示“当前没有有效条目”，不使用空壳对象作为占位。
* `StateManager` 会在读写阶段执行 schema 校验；缺文件、坏 JSON 或结构非法时会回退到默认状态。
* 非法状态回退不会静默吞掉，诊断输出中会包含 `state_validation_errors` 便于排查。
* 运行态状态默认写入仓库根目录下的 `.forgeflow/state/`，而不是直接写回本目录。

字段级详细说明见 [../docs/state/contracts.md](../docs/state/contracts.md)。
