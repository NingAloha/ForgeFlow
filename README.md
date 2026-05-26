# ForgeFlow

[中文](./README.md) | [EN](./README_EN.md)

ForgeFlow 是一个面向软件工程语义稳定化的实验性系统。

它不是一个“万能 AI 自动编程 Agent”，也不是一个直接替你生成完整项目的黑箱工具。

ForgeFlow 当前关注的问题是：

```text
模糊用户意图
→ 结构化 artifact
→ 多轮澄清
→ 本地验证
→ 更稳定的工程输入
```

换句话说，ForgeFlow 试图把 AI 从“直接写代码的人”约束成：

```text
受限的 artifact transformer
```

系统的核心目标不是让 AI 一步到位完成开发，而是让软件工程过程中的中间产物变得：

- 显式
- 可检查
- 可验证
- 可追踪
- 可逐步稳定

---

## 当前状态

ForgeFlow 当前仍处于早期原型阶段。

已经实现的部分：

```text
llm/
  最小 OpenAI-compatible LLM 调用原语

sieves/
  Requirement Clarifier 原型
```

当前已验证链路：

```text
用户输入
→ LLM JSON 输出
→ requirement artifact
→ 本地 schema 校验
→ 单问题澄清循环
→ refined requirement artifact
```

---

## 当前项目结构

```text
ForgeFlow/
├── llm/
│   ├── api.py
│   ├── llm_caller.py
│   └── prompts/
│       └── json_only_system.txt
│
├── sieves/
│   ├── requirement_clarifier.py
│   └── prompts/
│       └── requirement_system.txt
│
├── README.md
└── README_EN.md
```

---

## LLM Primitive

`llm/` 目前只负责一件事：

```text
system_prompt + user_prompt
→ OpenAI-compatible Chat Completion API
→ JSON object
```

它不负责：

- agent orchestration
- memory
- retries
- workflow
- schema semantics
- business logic
- tool calling
- code generation

当前核心接口：

```python
call_llm_json(system_prompt: str, user_prompt: str) -> dict
```

这只是 ForgeFlow 的底层 transport primitive。

---

## Requirement Clarifier

`Requirement Clarifier` 是 ForgeFlow 的第一个语义筛子。

它负责：

```text
raw user intent
→ validated requirement artifact
```

并通过 `unresolved_items` / `inconsistencies` 驱动单问题澄清循环。

当前 requirement artifact schema：

```json
{
  "goal": "string",
  "target_users": ["string"],
  "functional_requirements": ["string"],
  "constraints": ["string"],
  "acceptance_criteria": ["string"],
  "unresolved_items": ["string"],
  "inconsistencies": ["string"],
  "assumptions": ["string"]
}
```

当前本地校验只检查：

- 必填字段存在
- 不允许额外字段
- 字段类型正确
- list 元素必须是 string

它暂时不做：

- 语义验证
- 合规检查
- 安全策略判断
- artifact 持久化
- 历史记录
- rollback
- downstream design 生成

---

## 运行方式

创建虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install openai python-dotenv
```

项目根目录创建 `.env`：

```env
MODEL_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=your_api_key
MODEL_NAME=your_model_name
```

运行 LLM 调用测试：

```bash
.venv/bin/python -m llm.llm_caller
```

运行 Requirement Clarifier：

```bash
.venv/bin/python -m sieves.requirements.requirement_clarifier
```

---

## 当前设计原则

### 1. 小 primitive 优先

ForgeFlow 当前不追求完整架构。

优先验证：

```text
小模块
真实可跑
边界清楚
可逐步组合
```

而不是提前构造：

- runtime
- orchestrator
- plugin system
- provider abstraction
- agent framework

---

### 2. Artifact 优先于对话历史

ForgeFlow 不希望系统长期依赖自由对话上下文。

当前方向是：

```text
当前 artifact + 用户澄清
→ refined artifact
```

而不是：

```text
完整聊天记录
→ 重新猜测需求
```

---

### 3. Prompt 是 artifact

ForgeFlow 把 prompt 视为语义转换规则，而不是临时字符串。

因此 prompt 被放在：

```text
llm/prompts/
sieves/prompts/
```

并通过文件进行版本管理。

---

### 4. JSON 不是语义稳定

ForgeFlow 不认为“模型返回 JSON”就等于系统稳定。

当前已经区分：

```text
JSON object
≠
valid requirement artifact
```

所以 Requirement Clarifier 增加了本地 schema validator。

---

## 长期方向

ForgeFlow 长期可能演化为多层语义筛选系统：

```text
User Intent
  ↓
Requirement Sieve
  ↓
Design Sieve
  ↓
Contract Sieve
  ↓
Test Sieve
  ↓
Implementation Sieve
  ↓
Verification Sieve
```

每一层都应该：

- 接收明确 artifact
- 检查结构合法性
- 暴露 unresolved items
- 标记 inconsistencies
- 输出更稳定的 artifact

---

## 长期核心对象

未来 ForgeFlow 可能包含：

- `RequirementSpec`
- `ModuleContract`
- `ContractGraph`
- `TestSuite`
- `IntegrationTestSuite`
- `VerificationResult`
- `FailureReport`
- `Assumption`
- `Revision`

但当前不会提前实现这些对象。

只有当下一个 sieve 真正需要它们时，才会引入。

---

## 当前明确不做

ForgeFlow 当前不做：

- 自动完整写代码
- 自主 agent loop
- 黑箱 runtime
- 自动 retry
- 自动 rollback
- 自动 commit
- 多 provider abstraction
- 复杂 workflow orchestration
- 安全 / 合规检查
- artifact persistence

这些都不是当前阶段的核心问题。

---

## 当前核心问题

ForgeFlow 现在最重要的问题不是：

```text
AI 能不能自动写代码？
```

而是：

```text
模糊软件需求能不能通过可控语义循环，
逐步收敛为结构稳定、可验证、可传递的 artifact？
```

如果这个问题不能成立，后面的 Design、Contract、Test、Implementation 都没有稳定基础。

---

## 当前里程碑

已完成：

```text
LLM transport primitive
Requirement clarification sieve prototype
Validated requirement artifact schema
Single-question refinement loop
```

下一步可能是：

```text
Requirement artifact
→ Design / Contract artifact
```

但在进入下一层之前，需要继续观察 Requirement Clarifier 是否足够稳定。
