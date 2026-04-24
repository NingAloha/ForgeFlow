# State Runtime

这里收运行态状态目录和 `StateManager` 的运行约定。

当前约定：

* 运行态状态默认写入仓库根目录下的 `.forgeflow/state/`
* 仓库内的 `state/` 目录保留为契约示例和字段参考
* 空列表表示“当前没有有效条目”，不使用空壳对象作为占位
* `StateManager` 在缺文件、坏 JSON 或结构不完整时会回退到默认状态并补齐缺失字段
* 状态保存使用原子写入路径，避免半写入污染主状态

配套阅读：

* [../contracts/README.md](../contracts/README.md)
* [../../state/README.md](../../state/README.md)
