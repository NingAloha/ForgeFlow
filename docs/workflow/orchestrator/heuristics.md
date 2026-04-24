# Heuristics And Simplifications

当前很多 blocker / issue 还没有完全结构化到足以直接判断根因层级，因此实现中保留了一些第一版文本归因策略。

主要输入：

* `implementation_status.blockers`
* `implementation_status.known_limitations`
* `test_report.issues[].title`
* `test_report.issues[].notes`

第一版归因会结合：

* `related_modules`
* `related_contracts`
* 文本中的关键词

当前关键词大致分为：

* 执行性问题：环境、依赖、工具链、权限、资源、网络等
* design 问题：contract、input、output、data flow、trigger、boundary、interface 等
* solution 问题：module、responsibility、ownership、stack、architecture、framework 等
* requirements 问题：requirement、acceptance、constraint、scope、priority、goal、mvp 等

当前仍保留的简化：

* `REQUIREMENTS`、`SOLUTION`、`DESIGN` 的判定仍以核心字段为主。
* `TESTING` 和 `DONE` 还没有更细粒度的“可交付但有中低优先级问题”的决策层。
* `source_stage` 通过状态痕迹推断，而不是持久化存储。
* blocker / issue 的根因归因仍然部分依赖关键词，而不是完全依赖结构化 schema。
