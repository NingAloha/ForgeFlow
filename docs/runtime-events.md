# Runtime Events (Append-only)

ForgeFlow 为每一次 run 提供两类历史产物：

- `events.jsonl`: append-only 的 run history 事件流（不重写、不回填）。
- `summary.json`: materialized snapshot（便于快速回放与人类阅读的汇总视图）。

## 文件位置

每个 run 的 events 固定写入：

```
.forgeflow/runs/<run_id>/events.jsonl
```

格式为 JSON Lines：每行一个 JSON object。

## 事件模型（v1）

事件字段：

```json
{
  "timestamp": "2026-05-15T09:30:00Z",
  "event_type": "decision_computed",
  "run_id": "...",
  "sequence": 1,
  "payload": {}
}
```

v1 的事件类型控制在 4 个以内：

- `run_started`
- `decision_computed`
- `stage_executed`
- `run_finished`

## Replay 语义

- 若 `events.jsonl` 存在：Replay 优先以事件流作为 timeline 来源。
- 若 `events.jsonl` 缺失：Replay fallback 到 `summary.json.steps`。

## 非目标（本阶段不做）

本 PR 不引入：

- telemetry / metrics
- websocket streaming / live dashboard
- async queue / distributed event bus
- OpenTelemetry / distributed tracing
- event subscribers
- agent memory
- execution semantics / orchestrator transition 修改

## 核心 invariant

Runtime events 记录历史；它们不控制执行流程。

