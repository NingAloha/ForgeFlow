# Orchestrator Implementation Notes

这一页记录当前 `Project Orchestrator` 的实现约定。它不替代工作流规则文档，而是解释规则落到代码时采用了哪些中间模型与简化策略。

## 这份文档回答什么

规则文档主要回答：

* 哪些状态应被视为 ready
* 哪些信号应触发回流
* 回流后哪些下游产物不再默认有效

而当前实现还需要回答一些更偏代码层的问题，例如：

* 布尔判定链如何组织
* “当前真相阶段”和“当前回流上下文阶段”如何区分
* 回流目标如何作用到阶段判定结果
* 某些尚未完全结构化的 blocker / issue 文本如何做第一版归因

这些约定记录在本页。

## 当前阶段判定模型

当前实现采用一组布尔链作为阶段真相来源：

* `requirements_ready`
* `solution_ready`
* `design_ready`
* `implementing_active`
* `testing_active`
* `done_ready`

这些布尔值按顺序依赖：

* `solution_ready` 只有在 `requirements_ready = true` 时才可能成立
* `design_ready` 只有在 `solution_ready = true` 时才可能成立
* `implementing_active` 只有在 `design_ready = true` 时才可能成立
* `testing_active` 只有在 `implementing_active = true` 时才可能成立
* `done_ready` 只有在 `testing_active = true` 时才可能成立

当前真相阶段取“最后一个成立的布尔值对应阶段”。

这个模型的核心思想是：

* 每个阶段先抽象成一个布尔判定，而不是直接维护单一 `current_stage` 字段
* 布尔值按主流程顺序形成单向链路
* 当前阶段不是独立存储出来的，而是由这条布尔链推导出来的最后一个成立阶段

可以把它理解成：

```text
requirements_ready
-> solution_ready
-> design_ready
-> implementing_active
-> testing_active
-> done_ready
```

其中：

* 如果前一层不成立，后一层原则上也不应成立
* 因此整条链天然适合表达单线程主流程
* “当前真相阶段”可以直接定义为这条链中最后一个 `true`

这套思路的好处是：

* 阶段真相来自规则计算，而不是来自单独维护的阶段字段
* 当上游前提失效时，阶段会自然沿链路下坠，不需要手工维护多处状态同步
* 回流时只需要明确“目标层之后哪些布尔值应被置为 `false`”，模型保持简单

当前实现就是按这个思路组织的。

这意味着：

* orchestrator 的 `computed_stage` 表示当前状态文件在严格判定下还能站到哪一层
* `computed_stage` 不承担“当前问题最初在哪一层暴露”的语义

## `computed_stage` 与 `source_stage`

当前实现中有两个容易混淆但必须区分的概念：

* `computed_stage`
* `source_stage`

`computed_stage`：

* 由阶段布尔链直接计算
* 代表当前状态文件在严格 ready / active 判定下成立到哪一层

`source_stage`：

* 用于回流判断的上下文阶段
* 当上游前提已经失效、导致 `computed_stage` 下坠时，仍可根据下游产物痕迹推断“问题原本是在哪一层暴露的”

当前 `source_stage` 通过以下痕迹推断：

* 如果已有 testing 结果或 testing issue，则优先视为 `TESTING`
* 否则如果 `implementation_status` 已进入活动状态，则视为 `IMPLEMENTING`
* 否则如果已有 design 结构、contract、data flow 或 MVP 交付定义，则视为 `DESIGN_READY`
* 否则如果已有 solution 技术主干或模块映射，则视为 `SOLUTION_READY`

## 回流目标与最终阶段

当前实现中，回流判断不是直接把 `current_stage` 改成目标阶段，而是分两步：

1. 先得到 `backflow_target`
2. 再把目标阶段之后的布尔链一路置为 `false`

例如：

* 如果回流目标是 `DESIGN_READY`
* 则 `implementing_active`、`testing_active`、`done_ready` 都会被置为 `false`
* 之后再重新根据布尔链计算最终阶段

这意味着：

* `backflow_target` 表示“应该退回哪一层重新处理”
* `final_stage` 表示“应用回流后，当前真相阶段最终落在哪”

两者不一定相同。

典型情况：

* 如果回流目标是 `REQUIREMENTS_READY`
* 但当前 requirements 本身已经不满足 ready 条件
* 则 `final_stage` 可能落到 `INIT`

这不是冲突，而是当前实现中“回流目标”和“阶段真相”被有意区分的结果。

用布尔链的语言来描述，当前回流实现可以概括为：

* 如果回流目标是 `IMPLEMENTING`
  就把 `testing_active` 和 `done_ready` 置为 `false`
* 如果回流目标是 `DESIGN_READY`
  就把 `implementing_active`、`testing_active`、`done_ready` 置为 `false`
* 如果回流目标是 `SOLUTION_READY`
  就把 `design_ready` 以及其后的布尔值置为 `false`
* 如果回流目标是 `REQUIREMENTS_READY`
  就把 `solution_ready` 以及其后的布尔值置为 `false`

然后再重新取“最后一个成立的布尔值”作为最终阶段。

这是当前实现采用布尔链模型后最重要的一个配套约定。

## 当前第一版归因策略

当前很多 blocker / issue 还没有完全结构化到足以直接判断根因层级，因此实现中保留了一些第一版文本归因策略。

目前主要用于：

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

这一层实现属于当前版本的简化策略，不应被误解为最终归因模型。

## 当前实现中仍然保留的简化

以下内容当前仍是有意简化，尚未完全按文档细化到最终形态：

* `REQUIREMENTS_READY`、`SOLUTION_READY`、`DESIGN_READY` 的判定仍以核心字段为主，没有覆盖所有建议项与软条件。
* `TESTING` 和 `DONE` 目前没有引入更细粒度的“可交付但有中低优先级问题”的决策层。
* `source_stage` 目前通过状态痕迹推断，而不是持久化存储。
* blocker / issue 的根因归因仍然部分依赖关键词，而不是完全依赖结构化 schema。

这些简化是当前为了先建立稳定骨架而保留的，不表示规则文档本身已经收缩到这个粒度。

## 与规则文档的关系

* [workflow_criteria.md](./workflow_criteria.md)：工作流入口与总览
* [workflow_stage_criteria.md](./workflow_stage_criteria.md)：正向阶段进入条件
* [workflow_backflow_rules.md](./workflow_backflow_rules.md)：回流规则与状态失效处理
* [state_contracts.md](./state_contracts.md)：状态字段契约

如果未来实现与规则文档出现冲突，应优先回到规则文档澄清，再调整实现，而不是长期保留“代码真相”和“文档真相”两套规则。
