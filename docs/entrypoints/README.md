# Entrypoint Docs

这里收项目入口层的职责划分说明。

当前约定：

* ForgeShell / TUI 是目标主交互入口
* 当前仓库可运行的主入口仍是 `main.py`（开发、调试 runner）
* `main.py` 支持 `--state-dir` 用于隔离演示/调试状态目录
* `main.py` 支持 `--auto-run` 连续推进，直到 `DONE` 或 `WAIT`
* LLM 密钥解析优先级固定：`api_key`（或 `FORGEFLOW_LLM_API_KEY`）优先，其次才是 `api_key_env` 指向的环境变量值（默认 `DEEPSEEK_API_KEY`）

相关入口说明：

* [../../README.md](../../README.md)
* [../README.en.md](../README.en.md)
