# Entrypoint Docs

这里收项目入口层的职责划分说明。

当前约定：

* ForgeShell / TUI 是目标主交互入口
* 当前仓库可运行的主入口仍是 `main.py`（开发、调试和一次性诊断 runner）
* `main.py` 支持 `--state-dir` 用于隔离演示/调试状态目录

相关入口说明：

* [../../README.md](../../README.md)
* [../README.en.md](../README.en.md)
