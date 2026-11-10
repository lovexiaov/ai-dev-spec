# Spec: AI 交互事件（AgentLog 六端统一）

> 复制 `docs/specs/_template` 为 `docs/specs/ai-events/` 后填写。
> 语言中立契约真源：`docs/logging-framework/INTERFACE.md` + 线格式 `docs/logging-framework/schema/log-event.schema.json`。
> 参考现状：Web 已有 `src/frontend/ai-events.ts`（自发实现，非标准字段名），其余五端完全空白。

## Goal（目标）

- 为六端日志框架（Python / Go / Java / Android / Web / macOS）补齐**统一的 AI 交互事件契约**，让任意端的 Agent / LLM 调用都能产出结构一致、可被下游程序化过滤与聚合的事件。
- 成功长什么样：任一端调用 `record_ai_response(...)`（或等价 API），产出一行合法 Schema v1.4 JSONL——`event_type` 为标准 AI 值、`payload` 用标准词表（snake_case）、六端 OTLP 映射一致。下游无需按端分支即可按 `event_type` + `request_id` 串联「请求→响应→工具→错误」同一轮对话。

## Non-goals（非目标）

- 本期**不做** LLM span 的自动产出：OTLP 层 AI 事件只作为 **log 信号**（可挂 `span_id` 供下游组 span），不产 `Span`。
- 本期**不实现**具体 LLM SDK 集成（不 hook OpenAI / Anthropic / 国产模型客户端），仅定义数据契约与便捷方法，由业务代码显式埋点。
- 本期**不引入** prompt / response 的语义分析、token 计费或成本统计。
- 沿用 §4.3 非目标：不做 Sentry / Datadog / APM 上报、不做 breadcrumb、不做 `stack` 结构化。

## Constraints（约束）

- **C1 遵守 Schema v1.4（本期升版，向后兼容增量）**：所有 AI 事件 = 单行 JSON；`event_type` 为标准 AI 值；非保留字段进 `payload`。
- **C2 线格式唯一**：字段名所有端逐字相同（snake_case）。`event_type` 取值见 §Interfaces；标准 payload 词表见 §Interfaces。
- **C3 复用既有契约**：`ai_error` 复用 v1.3 异常 payload 词表（`exception` / `exception_message` / `stack` / `mechanism`）；`trace_id` / `span_id` 沿用 v1.2 / v1.1 模型。
- **C4 脱敏**：`prompt_text` / `tool_arguments` / `system_prompt` 视为潜在敏感内容，默认走全局脱敏键（不可关闭）；若调用方额外声明红字段，按 `redact` 追加规则处理。不新增网络层脱敏逻辑。
- **C5 验收门槛**：六端均须有 `AiEventTests` 断言输出 `event_type` 为标准值、`payload` 用标准词表、字段集不泄漏 camelCase 别名；`xlang_verify` 须含一条 AI 样例且六端 OTLP log record 一致、且**均不产 span**。

## Interfaces（接口 / 数据契约）

### AI `event_type` 值集（6 个，snake_case）

| event_type               | 含义                    | 推荐 level | agent_auto |
| ------------------------ | ----------------------- | ---------- | ---------- |
| `ai_request_initiated`   | 一次 LLM 调用的请求发起 | info       | false      |
| `ai_response_received`   | 收到模型响应            | info       | false      |
| `ai_tool_call_initiated` | 工具调用发起            | info       | false      |
| `ai_tool_call_completed` | 工具调用完成            | info       | false      |
| `ai_guardrail_triggered` | 护栏 / 合规拦截触发     | warn       | false      |
| `ai_error`               | AI 交互出错             | error      | false      |

> `agent_auto=false`：AI 事件是业务代码**显式埋点**（框架提供便捷方法），区别于 crash / network 的自动埋点。

### 标准 payload 词表（snake_case，置于 `payload`）

所有端统一以下键（缺省即不写，不强制）：

- `ai_request_initiated`：`model`、`provider`、`prompt_text`、`system_prompt`(可选)、`messages_count`、`request_id`
- `ai_response_received`：`model`、`provider`、`response_length`、`prompt_tokens`、`completion_tokens`、`total_tokens`、`finish_reason`、`latency_ms`、`request_id`
- `ai_tool_call_initiated`：`tool_name`、`tool_arguments`(任意 JSON 结构)、`request_id`
- `ai_tool_call_completed`：`tool_name`、`tool_call_latency_ms`、`ok`(bool)、`request_id`
- `ai_guardrail_triggered`：`guardrail_type`、`reason`、`request_id`
- `ai_error`：复用 `exception` / `exception_message` / `stack` / `mechanism` + `request_id`

`request_id`（可选）：用于串联「请求→响应→工具→错误」同一轮对话；若存在，应跨该轮所有 AI 事件保持一致。框架不强制生成。

### 线格式示例（Schema v1.4）

```json
{
  "ts": "2026-11-10T13:37:21.123Z",
  "level": "info",
  "service": "web-app",
  "event_type": "ai_response_received",
  "session_id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
  "agent_auto": false,
  "message": "ai response received",
  "env": "prod",
  "release": "1.4.0",
  "payload": {
    "model": "gpt-4o",
    "provider": "openai",
    "response_length": 1280,
    "prompt_tokens": 320,
    "completion_tokens": 210,
    "total_tokens": 530,
    "finish_reason": "stop",
    "latency_ms": 842,
    "request_id": "req_001"
  }
}
```

### 各端 API（语义等价，命名随语言惯例）

- **Python**：`record_ai_request(model, prompt_text, **kw)` / `record_ai_response(model, total_tokens, **kw)` / `record_ai_tool_call(tool_name, tool_arguments, **kw)` / `record_ai_tool_result(tool_name, ok, **kw)` / `record_ai_guardrail(guardrail_type, reason, **kw)` / `record_ai_error(error_type, message, **kw)`
- **Go**：`RecordAIRequest(...)` / `RecordAIResponse(...)` / `RecordAIToolCall(...)` / `RecordAIToolResult(...)` / `RecordAIGuardrail(...)` / `RecordAIError(...)`
- **Java**：`AgentLog.aiRequest(...)` / `AgentLog.aiResponse(...)` / `AgentLog.aiToolCall(...)` / `AgentLog.aiToolResult(...)` / `AgentLog.aiGuardrail(...)` / `AgentLog.aiError(...)`
- **Android**：`AgentLog.aiRequest(...)` / …（同 Java 形态）
- **macOS**：`Logger.aiRequest(...)` / …（`record` 入口盖章 `event_type`/`level`/`agent_auto`）
- **Web**：修正现有 `logAiRequest` / `logAiResponse` / `logAiToolCall` / `logAiToolResult` / `logAiGuardrail` / `logAiError`（保留函数名，改 payload 字段为标准词表、明确 level、传 `agentAuto: false`）

## Acceptance Criteria（可测验收条件）

- [x] `AiEventTests`：任一 `record_ai_*` 产出行的顶层键 ⊆ Schema v1.4 必填+可选集；`event_type` ∈ 上述 6 值；`payload` 只含标准词表键（或调用方自定义业务键），**不得出现 camelCase 别名**（`promptText`→`prompt_text`、`tokenUsage`→`total_tokens` 等）。
- [x] 不出现 camelCase / 历史别名泄漏到线上（各端 AI 测试断言 `promptText`/`tokenUsage`/`toolCallLatency` 等不在输出）。
- [x] `ai_error` 产出的 `payload` 含 `exception` / `exception_message` / `mechanism=handled`（stack 可选），且 `level=error`、`agent_auto=false`。
- [x] `level` 词表只允许 6 档；AI 事件级别命中上表约定（request / response / tool = info，guardrail = warn，error = error）。
- [x] 跨端一致：`xlang_verify` 含 2 条 AI 样例（`ai_response_received` 带 token 数据 + `request_id`、`ai_error` 带异常词表），六端 OTLP log record 属性一致且**均不产 span**（逐端 traces 均只有 HTTP/DB 两条 span）。
- [x] 六端均可本地 / CI 跑通对应测试（python 115 / go ok / java 66 / android 61 / web 68 / macos 70）；macOS 真实 XCTest 由 CI 兜底。
- [x] 不破坏既有事件（network_request / crash / log 等）的 schema 合法性（v1.3 行仍合法 → v1.4 兼容）。

## Done when（完成定义）

- Schema 升 v1.4（主副本 + go / python / java / android 副本 + templates/base 同步），INTERFACE.md 新增 AI 事件段；六端实现统一的 AI 便捷 API + 测试通过；Web `ai-events.ts` 修正为标准词表；`xlang_verify` 含 AI 样例且六端一致；发布时 SDK 版本与 schema 同步升到 `1.4.0`（六端 tag `v1.4.0`，`telemetry.sdk.version` 六端一致）；相关 CHANGELOG / README 已更新；7 仓 CI 全绿。
