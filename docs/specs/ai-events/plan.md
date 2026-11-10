# Plan: AI 交互事件（AgentLog 六端统一）

> 只写「本次实现真正会用到的设计决策」，不重复 AGENTS.md / constitution 已有的全局约束。

## 模块边界

### 契约层（六端共享，一次改）

- `docs/logging-framework/schema/log-event.schema.json`（主副本）：`version` `1.3.0`→`1.4.0`；`event_type` 的 description 增补 6 个 AI 值；根 `description` 增补 v1.4 向后兼容增量说明。
- 副本同步（改主副本后必须 `cp` 同步，**web / macos 无副本**）：
  - `logging-framework/go/AgentLog/docs/schema/log-event.schema.json`
  - `logging-framework/python/AgentLog/docs/schema/log-event.schema.json`
  - `logging-framework/java/AgentLog/docs/schema/log-event.schema.json`
  - `logging-framework/android/AgentLog/docs/schema/log-event.schema.json`
  - `templates/base/docs/logging-framework/schema/log-event.schema.json`
- `docs/logging-framework/INTERFACE.md`：新增 §4.4「AI 交互事件」，列 event_type 值集、payload 标准词表、level 约定、`agent_auto=false`、非目标（不产 span）。

### 六端实现

- **python** `agentlog/`：新增 `ai_events.py`（`record_ai_*` 系列，封装既有 emit，设 `event_type` + `level` + `agent_auto=false`）；`coretypes.py` 的 `EventType` 增补 6 个 AI 值；`__init__.py` 导出；`tests/` 加 `AiEventTests`。
- **go** `agentlog/`：`event.go` 增补 AI `EventType` 常量；新增 `ai.go`（`RecordAIRequest` 等）；补测试。
- **java** `src/main/java/cn/lovexiaov/agent/log/`：`CoreTypes.java` 增补；新增 `AiEvents.java`；补测试。
- **android** `agentlog-core`：`CoreTypes.kt` 增补；新增 `AiEvents.kt`；core 测试。
- **web** `Obs`：`src/frontend/ai-events.ts` 修正为标准词表 + 明确 level + `agentAuto:false`（**保留函数名**）；`src/types.ts` 可加 AI `EventType` 类型；测试修正。
- **macos** `Sources/AgentLog/`：`Model.swift` `EventType` 增补；新增 `AiEvents.swift`（或扩展 `Logger`/`AgentLog`）；补测试。

### 一致性 & 文档

- `tools/otlp-compat-verify/xlang/samples.json` 加一条 AI 样例（`ai_response_received` + token 数据 + `request_id`）；harness（Dump.kt / main.swift / XlangMain.java）无需改（通用 emit）。
- 六端 `CHANGELOG.md`（先写 `[Unreleased]`，发布时定稿 `[1.4.0]`）、`README.md` AI 段落。

## 数据流

业务调用 `record_ai_response(model, total_tokens, request_id=...)` → 端内便捷方法组装 `event_type="ai_response_received"` + `level=info` + `agent_auto=false` + 标准 payload（snake_case） → 走各端唯一写入入口（Python `_build_event` / Go `Logger` / Java `buildEvent` / Android `Logger` / Web `emit` / macOS `record()`） → snake_case 线格式 JSONL + 脱敏。

OTLP 导出：AI 事件经 `event_to_log_record` / `event_to_span`，`_span_kind` 对 AI 类型返回 `None` → **只产 log record，不产 span**；payload 作为 `payload.*` 属性，异常类（仅 `ai_error`）走 `_exception_attributes`。

`request_id` 由调用方在「请求→响应→工具→错误」同一轮内保持一致，用于下游串联；框架不强制生成、不校验。

## 本次特有的实现选择

- **D1 event_type 值集**：沿用 Web 既有 6 值（`ai_request_initiated` 等），不重新命名，避免 Web 再改。
- **D2 payload 词表**：自拟一组 snake_case 标准键，**不硬绑 OpenTelemetry `gen_ai.*`**，保持框架中立、数据由下游自行映射；token 拆 `prompt_tokens` / `completion_tokens` / `total_tokens`（对齐业界惯例）。
- **D3 level / agent_auto**：命中 spec 上表约定；AI 事件一律 `agent_auto=false`。
- **D4 OTLP 不产 span（关键决策，待批准）**：AI 事件本期只作为 log 信号，保持最小改动与「数据生产者」定位；允许携带 `span_id` 供下游组 span。理由：产 span 涉及 gen_ai span 语义（命名 / 属性）是更大的范围，且下游 OTel 集成可自行基于 `event_type` 组 span，不阻塞本期。
- **D5 API 形态**：六端各加一组语义化 `record_ai_*` / `aiRequest` 便捷方法（非仅通用 emit），降低调用方拼 payload 的心智负担；内部复用既有写入入口。
- **D6 版本**：Schema v1.3→v1.4（向后兼容增量）；发布时 **SDK_VERSION 与 schema 同步升 1.4.0**（六端 tag `v1.4.0`，延续上次 1.3.0 节奏），`telemetry.sdk.version` 六端一致。
- **D7 Web 兼容**：保留 `logAi*` 函数名，仅改 payload 字段名与 level / `agentAuto`，不破坏既有调用方签名。

## 必须 break 的旧路径

- Web `ai-events.ts` 旧字段名（`promptText` / `toolName` / `toolArguments` / `tokenUsage` / `responseLength` / `guardrailType` / `errorType` / `errorMessage`）→ 标准 snake_case 词表。旧调用方若直接读这些 camelCase 键需更新（破坏性仅限于 AI 事件，范围小）。
- 其余五端为全新，无旧实现可替换。

## 风险与缓解

| 风险                                                | 缓解                                                        |
| --------------------------------------------------- | ----------------------------------------------------------- |
| payload 词表命名与下游 OTel 不一致                  | 保持框架中立（不硬绑 `gen_ai.*`），文档说明映射；下游按需转 |
| Web 既有调用方依赖 camelCase 字段                   | 破坏性仅限 AI 事件且范围小；CHANGELOG 明示 + 提供迁移说明   |
| xlang AI 样例因 number-model（int vs double）差异挂 | xlang 校验已容忍 int/double；token 用 int 保持一致          |
| 缺少 `span_id` 导致下游组 span 断链                 | 文档明确要求需要 span 的调用方显式传 `span_id`              |
| schema 副本同步遗漏（某端仍 1.3.0）                 | `cp` 同步 + xlang / CI 校验；改主副本后必须同步五副本       |

---

## ✅ Human Approval

> Agent 在获得本区块人工勾选前，**不得修改 `src/`**（契约文档 `docs/` 可先写）。
> 本特性涉及六端跨语言改动，建议人工审阅以下架构决策后再扩到全量实现：

- [x] 架构 / 设计已审阅（6 个 AI event_type + 标准 payload 词表 + **OTLP 不产 span (D4)** + v1.4 / 1.4.0 发布），批准进入实现阶段
  - 批准方式：会话内 `AskUserQuestion` 明确选定「**批准 · 不产 span**」（2026-11-10）
  - D4 结论：AI 事件在 OTLP 层只作 log 信号（可挂 `span_id` 供下游组 span），不产 `Span`；
    `ai_error` 复用 v1.3 异常词表并映射为 `exception.*` 属性。
