# Logging Interface（语言中立的日志接口规范）

> **语言无关**。定义「一个合规 logger 必须实现什么」，是统一日志框架的契约真源。
> 各语言实现（`web/Observability` 的 TypeScript、`macos/AgentLog` 的 Swift …）都必须 conform 本规范。
> 线格式（wire format）由 `schema/log-event.schema.json` 定义，本文件定义**方法面**。

## 1. 必实现方法

| 方法 | 签名（伪代码） | 语义 |
| --- | --- | --- |
| `emit` | `emit(event: LogEvent): void` | 接收结构化事件 → 映射为 Schema v1（snake_case）→ 脱敏 → 写出。 |
| `child` | `child(context: Partial<LogEvent>): Logger` | 返回一个合并了 `session_id / user_id / subsystem / env` 等作用域 logger。 |
| `setLevel` | `setLevel(level: Level): void` | 设置最低输出级别（见 §3 词表）。 |
| `redact` | `redact(paths: string[]): void` | **追加**脱敏路径；默认脱敏键**不可关闭**。 |

## 2. 一致性约束（conformance）

- 每条经 `emit` 写出的记录 MUST 能通过 `schema/log-event.schema.json` 校验（字段集封闭、snake_case、必填齐全）。
- 调用侧仍可用 camelCase 书写（`event` / `traceId` / `userId`），由 logger 在**序列化边界**映射为 snake_case 线格式。
- 非保留键（如业务字段 `amount`、`orderId`）MUST 进入 `payload` 对象，不得泄漏到顶层。
- 脱敏 MUST 在 logger 层拦截，不依赖调用方自觉。
- 统一追踪模型：`trace_id` 与 `span_id` 共同标识一次分布式链路——`trace_id` 串联整个请求链路，`span_id` 标识其中的**一次操作**（如一次 HTTP 调用 / 一次 DB 查询）。`trace_id` MUST 为 32 位小写十六进制（8 字节，与 OTLP `traceId` / W3C `traceparent` 的 trace-id 同构），大写输入归一为小写，其余任何值在序列化边界 MUST 丢弃该字段（事件照写），绝不派生或变形。`span_id` MUST 为 16 位小写十六进制（8 字节，与 W3C `traceparent` 的 span-id 同构），与该链路已有的 `trace_id` 一并写出；缺失时由导出端确定性派生（六端一致、幂等）。两者均可省略（无链路信息时都不写），由导出端决定派生策略。

## 3. Level 词表（与 Schema v1 一致）

`trace | debug | info | warn | error | critical`（6 档，全小写）。

## 4. 异常与版本（Schema v1.3）

框架只负责**把数据准备齐全**，不做上报 / APM 集成 / 崩溃落盘——具体怎么用由下游决定。

### 4.1 `release`（顶层可选字段）

- **来源**：配置项（`config.release` / `AgentLogConfig(release:)` / `LoggerOptions.release`），**不是**每次调用的参数。
- **盖章位置**：logger 的唯一写入入口（`record()` / `emit()` 组装事件时从配置取）。`child()` 必须继承；自动埋点事件走同一路径；由采集点直接构造事件的分支（如崩溃）MUST 显式透传。
- **校验**：不校验格式（semver / git sha / build number 均可），仅要求**非空且 ≤128 字符**；不满足则视同未配置、**不写该键**（绝不写出 schema 违规行）。
- **缺省**：未配置时不写该键，因此 v1.2 的产出形态保持合法。

### 4.2 异常 payload 词表

崩溃 / 卡顿 / AI 调用失败等采集点 MUST 按下列键写入 `payload`（详见 `README.md` §3.5）：

`exception`（类型名）、`exception_message`（原始消息）、`stack`（**单字符串**，原生格式）、`mechanism`（`uncaught` / `handled` / `reported`）。

- 端特有兜底键（macOS `raw`、Web `componentStack`、Python `thread`）可与标准键并存，但**不得替代**标准键。
- 归一化发生在**采集点**（crash handler / ErrorBoundary / panic wrapper），OTLP 与序列化层不做二次加工。
- 解析失败 MUST NOT 抛错、MUST NOT 丢弃事件：标准键缺省，兜底键仍在。

### 4.3 明确非目标

框架不实现：Sentry / Datadog / APM 上报、breadcrumb、`stack` 的结构化 frames、崩溃事件落盘与重放（交宿主 sink 决定）。这些能力若需要，由下游基于上述数据自行构建。

### 4.4 AI 交互事件（Schema v1.4）

框架为 AI / Agent 调用提供统一的事件契约，让任意端的 LLM 调用都产出结构一致、可被下游按 `event_type` 程序化过滤、按 `request_id` 串联的事件。

**6 个标准 `event_type`（snake_case）**：

| event_type | 含义 | 推荐 level | agent_auto |
| --- | --- | --- | --- |
| `ai_request_initiated` | 一次 LLM 调用的请求发起 | info | false |
| `ai_response_received` | 收到模型响应 | info | false |
| `ai_tool_call_initiated` | 工具调用发起 | info | false |
| `ai_tool_call_completed` | 工具调用完成 | info | false |
| `ai_guardrail_triggered` | 护栏 / 合规拦截触发 | warn | false |
| `ai_error` | AI 交互出错 | error | false |

- `agent_auto=false`：AI 事件是业务代码**显式埋点**（框架提供便捷方法），区别于 crash / network 的自动埋点。
- **标准 payload 词表**（snake_case，置于 `payload`，缺省即不写）：
  - `ai_request_initiated`：`model`、`provider`、`prompt_text`、`system_prompt`(可选)、`messages_count`、`request_id`
  - `ai_response_received`：`model`、`provider`、`response_length`、`prompt_tokens`、`completion_tokens`、`total_tokens`、`finish_reason`、`latency_ms`、`request_id`
  - `ai_tool_call_initiated`：`tool_name`、`tool_arguments`(任意 JSON)、`request_id`
  - `ai_tool_call_completed`：`tool_name`、`tool_call_latency_ms`、`ok`(bool)、`request_id`
  - `ai_guardrail_triggered`：`guardrail_type`、`reason`、`request_id`
  - `ai_error`：复用 §4.2 异常词表 `exception` / `exception_message` / `stack` / `mechanism` + `request_id`
  - `request_id`（可选）：串联「请求→响应→工具→错误」同一轮对话；若存在应跨该轮保持一致，框架不强制。
- **脱敏**：`prompt_text` / `tool_arguments` / `system_prompt` 视为潜在敏感内容；沿用各端既有的全局脱敏键（不可关闭）与自由文本正则，不新增 AI 专属脱敏逻辑。需要整键掩码的业务字段由调用方通过 `redact` 追加。
- **OTLP 映射（与 §4.3 一致）**：AI 事件只作为 **log 信号**导出（`event_to_log_record`），**不产 span**；可携带 `span_id` 供下游基于 `event_type` 自行组 span。`ai_error` 因复用 §4.2 异常词表，与 `crash` / `hang` 一样额外映射为 OTel `exception.type` / `exception.message` / `exception.stacktrace` 属性（仍在 LogRecord 内，不产 span）。

## 5. 配置（语言中立）

统一读取 `config/logging.config.json`（Schema：`config/logging.config.schema.json`）。
各语言实现解析同一份 JSON，保证「换语言不改配置」。
