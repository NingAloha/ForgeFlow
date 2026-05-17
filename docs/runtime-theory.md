# ForgeFlow Runtime Theory

> 本文档描述 ForgeFlow Runtime v0 当前形成中的 runtime 模型与架构方向。
>
> 部分章节描述已经实现的 runtime semantics，
> 部分章节则描述可能的未来 runtime 方向。

---

# 1. Runtime 已经超越 “SE Pipeline”

ForgeFlow 最初起源于一个分阶段的软件工程流水线：

```text
Requirements → Solution → Design → Implementation → Testing
```

但随着 runtime semantics 的逐渐稳定，ForgeFlow 已经不再只是一个
“软件开发 pipeline”。

在 ForgeFlow Runtime v0 中：

- ForgeFlow Core 是 runtime governance layer
- ForgeFlow SE 是第一个 domain profile

这意味着系统定义从：

> “AI 软件工程流水线”

逐渐转变为：

> “受治理的 AI workflow runtime”

ForgeFlow 当前真正尝试解决的问题，也不再只是：

> “如何让 AI 生成软件”

而是：

> “如何通过 runtime contract，让 AI 与现实的交互变得可治理”

---

# 2. Core / Profile / Skill

ForgeFlow 正逐渐收敛为一个三层 runtime 架构。

## 2.1 Core Runtime

Core Runtime 负责 runtime governance semantics。

包括：

- state management
- replay
- lineage
- approvals
- events
- mutation gates
- rerun semantics
- runtime artifacts

Core Runtime 的核心职责是：

> 以可治理、可审计、可回放的方式，
> 管理 AI 与现实之间的交互。

Core Runtime 本身不依赖具体领域。

---

## 2.2 Profile

Profile 定义领域级 workflow grammar。

第一个 profile 是：

```text
ForgeFlow SE
```

Profile 可以定义：

- stages
- artifact contracts
- dependency semantics
- review semantics
- workflow structure

Profile 负责描述：

> 某个领域如何组织工作流。

但 Profile 本身不负责 runtime governance。

---

## 2.3 Skill

Skill 定义具体能力。

例如：

- Git interaction
- patch generation
- search
- pytest execution
- file materialization

Skill 不是 workflow。

Skill 是：

> 局部的现实操作能力。

Skill 会被 profile actors 或 runtime 使用，
但它本身不决定 workflow semantics。

---

# 3. Profile Actors 与 Runtime 的分离

最初的工程师 agents：

- Requirements Engineer
- Solution Engineer
- System Designer
- Implementation Engineer
- Test Validation Engineer

已经不再被视为 runtime 本身。

它们正在逐渐收敛为：

```text
ForgeFlow SE profile actors
```

这意味着：

- runtime 负责 governance semantics
- actors 负责在 contract 内完成领域任务

系统因此开始分离：

- workflow governance
与：
- domain-specific execution

---

# 4. Artifactized Runtime Memory

ForgeFlow Runtime v0 正逐渐将 memory 视为：

```text
结构化 runtime artifacts
```

而不是隐藏在 prompt/context 中的状态。

典型 artifacts 包括：

- `events.jsonl`
- `summary.json`
- `lineage.json`
- `review_state.json`
- `approvals/*.json`
- `rerun_plan.json`
- `execution_request.json`

这些 artifacts 共同构成：

```text
runtime operational memory
```

这与很多依赖：

- vector memory
- long prompt memory
- scratchpad memory

的系统不同。

ForgeFlow 更倾向于：

- structured operational memory
- replayable artifacts
- explicit lineage
- governed state transitions

因此 runtime 对隐藏上下文的依赖会逐渐降低，
而更多依赖 materialized semantic state。

---

# 5. Patch-Scoped Development

ForgeFlow Runtime v0 的一个重要方向是：

```text
patch-scoped development
```

传统 agent 系统往往要求：

> 一个 agent 同时理解整个项目。

这会导致：

- context explosion
- token inefficiency
- cache instability
- replayability 较弱
- parallelism 较差

ForgeFlow 正逐渐转向：

```text
runtime + artifacts + contracts + lineage
```

这使系统能够把开发拆解为：

```text
governed patches
```

在这种模型下，
actor 不再需要理解整个项目。

Runtime 只需要提供：

- relevant artifacts
- relevant contracts
- dependency state
- allowed file scope
- invariant tests

于是：

> 对“大上下文”的依赖，
> 被 runtime structure 主动拆解。

系统关注的问题因此从：

> “如何让一个 agent 理解整个世界”

转变为：

> “如何把现实拆解为 governed runtime patches”

这是一个非常重要的架构变化。

---

# 6. Tree-Based Readiness 与 Invalidation

ForgeFlow 最初更多使用线性 rollback 模型：

```text
Testing failure
→ rollback to Implementation
→ rollback to Design
```

未来可能的 runtime 方向是：

```text
semantic dependency tree
```

在这种模型下：

- readiness 会沿 dependency graph 传播
- invalidation 会沿 downstream nodes 传播
- execution 会受 dependency readiness gating

这可能逐渐替代大量线性 orchestration 逻辑。

未来可能出现的 runtime semantics 包括：

- readiness propagation
- invalidation propagation
- dependency gating
- tree-scoped rerun planning

系统可能逐渐从：

```text
central orchestration intelligence
```

转向：

```text
tree state driven workflow progression
```

本章节描述的是：

```text
possible future runtime direction
```

目前尚未在 Runtime v0 中完全实现。

---

# 7. Git 是 Substrate，而不是替代对象

ForgeFlow 不试图替代 Git。

更准确地说：

```text
Git = storage/history substrate
ForgeFlow = runtime semantics layer
```

未来 runtime-governed Git interaction
可能包括：

- gated mutation
- replayable changes
- branch-scoped execution
- governed patch application

当前 runtime principles 包括：

- `main` 始终 protected
- mutation 必须 gated
- `track/*` branch 表示 isolated runtime contract
- Git interaction 初期应保持 read-only 或 sandboxed

ForgeFlow 因此把 Git 视为：

> runtime 的基础设施，
> 而不是应该绕开的实现细节。

---

# 8. Governed Mutation

Runtime v0 实际完成的重点是：

```text
execution governance semantics
```

而不是 autonomous execution capability。

已经形成的 runtime semantics 包括：

- replay
- lineage
- approvals
- truth vs intent separation
- rerun semantics
- governed execution boundaries
- runtime artifacts

因此：

```text
execution 本身正在被 runtime contract 化
```

---

# 9. Runtime v0 与 v0.2 方向

Runtime v0 建立的是：

```text
ForgeFlow 的 control-plane semantics
```

下一阶段的重要目标，
并不是“让 AI 更强”。

而是：

```text
governed materialization
```

未来可能验证的 runtime 能力包括：

- sandbox writes
- controlled apply
- replayable mutation
- gated execution
- branch-scoped changes

核心目标是：

> 验证 execution semantics 是否能够被 runtime governance 承载。

而不是追求 unrestricted autonomy。

---

# 10. Runtime Direction

ForgeFlow 正逐渐从：

```text
prompt-driven agent systems
```

转向：

```text
contract-driven runtime systems
```

系统关注的重点，
已经不再是：

> “让 agent 更像人”

而是：

> “让 AI 与现实的交互变得：
>
> - 可治理
> - 可回放
> - 可审计
> - 可审批
> - 可局部失效
> - 可 patch 化
> - 可 contract 化”

这正在逐渐成为 ForgeFlow Runtime 的核心架构方向。