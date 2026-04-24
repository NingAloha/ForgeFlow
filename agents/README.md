# Agents Module

这个目录放各层 agent 与控制层角色实现。

关注点：

* `requirements_engineer.py`：需求规格生成；当前会从用户输入或已回答的 `question_state` 提取 `spec` 核心字段，并在缺关键字段时发起 blocking 澄清问题
* `solution_engineer.py`：方案与技术选型；当前会基于 `spec` 生成首版 `selected_stack`、`module_mapping`、`risks` 与 `alternatives`，并在 requirements 前提不足时发起 blocking 澄清问题
* `system_designer.py`：结构、契约与数据流设计
* `implementation_engineer.py`：实现与本地阻塞分析
* `test_validation_engineer.py`：验证、归因与回流输入
* `orchestrator.py`：流程调度入口
* `state_manager.py`：状态读写与一致性入口

如果你想看详细流程判定，请先读 [../docs/workflow_criteria.md](../docs/workflow_criteria.md)。
