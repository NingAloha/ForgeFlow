## Useful
- After 修复后，流程可以从同一输入推进到 `DONE`，并给出可读的 `spec / solution / design / implementation_status / test_report`。
- `implementation_status` 给出了明确的模块、文件触达与建议测试命令，用户可以据此开始手工实现。
- `test_report` 至少提供了可执行验证路径（`python3 -m unittest discover ...`）与运行结果摘要。

## Broken
- Before 修复时，Requirements 在 LLM 网络失败后直接阻塞到 `WAIT`，即使用户输入已经足够具体。
- Solution/Design 仍有“泛化命名”和“中文文本被机械切分”的问题（例如 `md` 作为模块名、需求语句切分不自然）。
- Testing 阶段当前验证的是生成模板的 smoke 测试，不是用户目标 CLI 的真实行为测试。

## Next Fix
- 本轮人工评分（1-5，越高越好）：
  - Requirements: **1 -> 3**
  - Solution: **2 -> 2**
  - Design: **2 -> 2**
  - Implementation: **2 -> 2**
  - Testing: **2 -> 2**
- 最低分阶段（按本轮评分表自动选）：**Solution**（与 Design/Implementation/Testing 并列最低，按上游优先原则先修 Solution）。

## Before/After 对比（仅本轮修复阶段）
- 修复阶段：Requirements
- Before：`retryable_error(network)` 直接触发 `WAIT`，`spec` 基本为空，仅有 `llm_generation_failed` 问题占位。
- After：在同样 `retryable_error(network)` 下，Requirements 使用已有规则抽取生成可用 `spec`，链路继续推进到 `DONE`。
- 副作用观察：
  - 正向：可用性显著提升，不再被网络波动完全阻断。
  - 风险：规则抽取质量一般，导致后续 Solution/Design 质量也一般，但这属于下一轮单阶段改进范围。

## Solution 对比（Phase 6）
- Solution score before: **2**
- Solution score after: **4**
- Broken 条目变化：
  - 已减少：
    - 模块名过短/无语义（`md`）
    - `tech_note` 为空，无法直接喂给 Design
    - alternatives 缺少明确非目标边界
  - 仍存在：
    - 某些中文需求切分仍偏机械（例如 `md_workflow_module` 的命名仍可更自然）
- 副作用检查：
  - 未观察到 orchestrator 流转副作用（同样到 `DONE`）
  - 未观察到 implementation/testing 退化
- 下一轮最低分阶段（人工评分）：**Design**

## Design 对比（Phase 7）
- Design score before: **2**
- Design score after: **4**
- Contracts 是否更具体：**是**
  - 从单一 `solution.module_mapping` 输入，提升到模块级输入 + 需求引用输入。
  - 输出增加 `implementation_status.<module>` 与 `test_report` 语义交接。
  - `failure_handling` 从回流模板改为语义级分类（`input_errors / processing_errors / output_errors / user_fixable / retryable`）。
- Project structure 是否更贴合 markdown CLI：**是**
  - 目录从泛化 `agents/*` 改为模块子目录 `src/<module>/`、`tests/<module>/`。
  - 未引入具体文件名/函数名/类名。
- Data flow 是否更可执行：**是**
  - trigger 从通用“Solution ready”改为 CLI 语义触发（markdown 输入与解析上下文）。
- 是否给 implementation 提供更明确输入：**是**
  - contract 约束与输出语义足够让 implementation_status 对齐文件触达、测试条目、合规状态。
- 副作用检查：
  - 未观察到 orchestrator 流转副作用（仍到 `DONE`）。
  - 未观察到 implementation/testing 退化。
- 下一轮最低分阶段（人工评分）：**Testing**

## Testing 对比（Phase 8）
- Testing score before: **2**
- Testing score after: **4**
- 测试范围是否对应 Design contracts：**是**
  - `issues` 在 contract 相关缺口时会绑定 `related_contracts`，并标注 `attribution=contract`。
  - 当 `tests_added_or_updated` 为空时会显式报告“无契约验证测试记录”。
- 是否覆盖错误分类语义：**是**
  - `input_errors`: 需求未决（`spec.open_questions`）
  - `processing_errors`: 实现未完成/阻塞、模块与设计结构不一致、契约合规失败
  - `output_errors`: 无测试记录、缺少 MVP 验证命令
- 是否说明验证命令：**是**
  - `test_report.command` 固定输出执行命令，执行轨迹含 suggested/executed command。
- issue 归因是否可区分 implementation / structure / contract：**是**
  - 通过 issue notes 中 `attribution=` 标签稳定区分。
- 副作用检查：
  - 未改 orchestrator/state contract/TUI/implementation，`ruff` 与 `pytest` 继续全绿。
- 下一轮最低分阶段（人工评分）：**Implementation**

