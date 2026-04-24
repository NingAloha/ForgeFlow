# `REQUIREMENTS` Criteria

`REQUIREMENTS` 表示需求已经足够清晰，可以进入 `SOLUTION` 阶段。

必须满足：

* `project_goal` 非空，且能清楚表达项目要解决的问题。
* `functional_requirements` 非空，且已经覆盖本轮要实现的主要能力。
* `acceptance_criteria` 非空，且至少能表达最关键的完成标准。

建议满足：

* `target_users` 尽量明确；如果是显然的自用项目或内部工具，可以允许极简描述。
* `constraints` 如果用户已明确提出，则必须记录；如果当前没有识别到硬约束，可以为空。
* `non_functional_requirements` 与 `preferences` 可以为空，但只要用户明确提过相关内容，就应被记录。

不能推进的情况：

* `open_questions` 中仍存在会阻塞方案设计的关键未决问题。
* 用户输入仍停留在模糊意图层，无法稳定提炼出主要功能需求。
* 验收标准过于空泛，导致后续无法判断“做到什么算完成”。
* 用户已经给出硬约束，但 `constraints` 尚未记录，或与现有需求描述冲突。

orchestrator 判断原则：

* 不以“字段是否全部填满”为 ready 标准，而以“是否已经足够进入方案设计”为准。
* 明确的新需求应直接进入正式需求字段；只有尚未澄清、会阻塞后续的问题才进入 `open_questions`。
* 如果需求内容已基本明确，但仍有非阻塞性小问题，可以先进入 `REQUIREMENTS`，并在后续阶段继续补全。
