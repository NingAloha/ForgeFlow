# TUI Module

这个目录放 ForgeShell 的终端交互层。

当前状态：

* 目录结构已保留，但 `tui/*.py` 仍是早期骨架文件。
* 现阶段实际可运行入口以根目录 `main.py` 的 CLI 诊断路径为主。

关注点：

* `app.py`：应用入口
* `screens.py`：页面或视图层
* `widgets.py`：组件层
* `commands.py`：命令系统
* `event_stream.py`：聊天流与事件流

如果你只想知道 TUI 在整体系统中的位置，先回根目录 `README.md`。
