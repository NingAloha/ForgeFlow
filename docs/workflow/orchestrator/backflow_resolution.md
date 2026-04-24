# Backflow Resolution

当前实现中，回流判断不是直接把当前阶段改成目标阶段，而是分两步：

1. 先得到 `backflow_target`
2. 再把目标阶段之后的布尔链一路置为 `false`

例如：

* 如果回流目标是 `DESIGN`
* 则 `implementing_active`、`testing_active`、`done_ready` 都会被置为 `false`
* 之后再重新根据布尔链计算最终阶段

这意味着：

* `backflow_target` 表示“应该退回哪一层重新处理”
* `final_stage` 表示“应用回流后，当前真相阶段最终落在哪”

两者不一定相同。比如回流目标是 `REQUIREMENTS`，但当前 requirements 本身已经不满足 ready 条件，`final_stage` 可能落到 `INIT`。

当前布尔链回退规则：

* 回流到 `IMPLEMENTATION`：清掉 `testing_active` 和 `done_ready`
* 回流到 `DESIGN`：清掉 `implementing_active`、`testing_active`、`done_ready`
* 回流到 `SOLUTION`：清掉 `design_ready` 及其之后
* 回流到 `REQUIREMENTS`：清掉 `solution_ready` 及其之后
