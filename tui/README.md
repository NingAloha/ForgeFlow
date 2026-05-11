# TUI Module

这个目录放 ForgeShell 的终端交互层。

当前状态：

* 当前提供最小 ForgeShell 壳（通过 `python main.py --tui` 启动）。
* TUI 只做可视化包装，不成为第二个控制面。
* 所有执行动作都通过既有 orchestrator API 转发。

关注点：

* `app.py`：应用入口
* `screens.py`：页面或视图层
* `widgets.py`：组件层
* `commands.py`：命令系统
* `event_stream.py`：聊天流与事件流

当前命令集（v1）：

* `/status`
* `/open spec`
* `/open solution`
* `/open design`
* `/run`

明确不在 v1 范围内：

* `/rollback`
* `/retry`
* `/switch`
* `/lock`

如果你只想知道 TUI 在整体系统中的位置，先回根目录 `README.md`。
