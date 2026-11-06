# Spec: Android Kotlin 日志框架（AgentLog for Android）

> 复制 `docs/specs/_template` 为 `docs/specs/android-logging/` 后填写。
> 这是 Agent 的「契约与唯一事实来源」，必须**可测**、**正向定义**为主。
> 上游真源：语言中立契约 `docs/logging-framework/INTERFACE.md` + 线格式 `docs/logging-framework/schema/log-event.schema.json` + 通用约束 `docs/logging-framework/README.md`（C1–C7）。
> 参考实现：`logging-framework/macos/AgentLog`（Swift，含 `SchemaTests`）、`logging-framework/web/Observability`（TS）。

## Goal（目标）

- 为 Android（Kotlin）App 提供**统一、面向 Agent（AI 调试/排障）**的日志接入规范，与 Web / macOS 端输出**逐字相同**的 Schema v1 线格式。
- 让业务侧**零改造**即可接入：一处 `bootstrap` + 默认全开的自动埋点（UI / 页面 / 网络 / 崩溃 / 卡顿），Agent 无需改业务代码即可观测。
- 成功长什么样：Android App 接入后，本地 `agent-log.jsonl` 中每一行都是合法 Schema v1 JSON，自动事件带 `agent_auto:true` 与明确 `event_type`，且 `SchemaTests` 断言字段集与 schema 一致。

## Non-goals（非目标）

- 本期**不做**云端上报 / 后端聚合（纯本地优先，C3）；如需云端，后续叠 exporter，不影响本期。
- 本期**不做** iOS / 其它端（各自仓库自维护，见 README §5）。
- 本期**不重写** Schema v1 或通用约束；任何线格式变更 = 升 schema 版本，由各端协同，不在本特性私加顶层字段。
- 本期**不引入**重量级 APM（Sentry / Datadog）；崩溃用轻量 `Thread.setDefaultUncaughtExceptionHandler` + 结构化落盘，不依赖第三方崩溃 SDK。

## Constraints（约束）

- **C1 遵守 Schema v1**：每条事件 = 单行 JSON（JSONL），字段严格遵循 `schema/log-event.schema.json`（顶层 `additionalProperties:false`）。非保留字段一律进 `payload`。
- **C2 线格式唯一**：字段名所有端逐字相同（snake_case）。Kotlin 内部可用 camelCase，但**只在序列化边界映射**；历史别名 `eventType/timestamp/sessionId` 等禁止漏到线上。
- **C3 本地优先 & 易导出**：本地持久化 JSONL + 一键导出；默认无云端依赖。
- **C4 业务零改造**：薄封装 `AgentLog`，一处 `bootstrap`；自动埋点默认全开。
- **C5 自动埋点默认全开（可关闭）**：覆盖 UI 交互/页面浏览、网络请求、崩溃/未捕获异常、性能/卡顿；自动事件统一 `agent_auto:true` + 明确 `event_type`。
- **C6 强制脱敏**：在 logger 层拦截；默认脱敏键 `password/token/authorization/cookie/secret` 等（覆盖 `api_key`/`access_token` 分隔符变体）；网络默认只记 `host/path/status/耗时/error`，不记 query 敏感参数与 body。
- **C7 验收门槛**：必须有 `SchemaTests` 断言输出字段集与 schema 一致；自动事件须可被 Agent 按 `event_type` 程序化过滤。
- **接口面（INTERFACE.md §1）必须实现**：`emit` / `child` / `setLevel` / `redact`。
- 模块结构遵循脚手架语言中立约定：核心逻辑放**纯 Kotlin/JVM**（`agentlog-core`，可在无 Android 环境下编译+测试），Android 平台胶水放 `agentlog-android`（AGP 库，依赖 core）。

## Interfaces（接口 / 数据契约）

### 业务手动日志（替代裸 Log/println）

```kotlin
AgentLog.info("user opened settings", category = "settings")
AgentLog.error("save failed", traceId = "trace_abc", payload = mapOf("reason" to "disk full"))
val child = AgentLog.child(mapOf("userId" to "u_123"))
child.debug("scoped log")
```

### 初始化（Application.onCreate 最早处）

```kotlin
AgentLog.bootstrap(context, AgentLogConfig(subsystem = "com.yourapp.agent"))
// 或按需关闭：AgentLogConfig(autoInstrumentation = setOf(AutoInstrumentation.NETWORK, AutoInstrumentation.CRASH))
```

### 线格式（Schema v1，与 Web/macOS 逐字相同）

```json
{
  "ts": "2026-11-02T13:37:21.123Z",
  "level": "info",
  "service": "com.yourapp",
  "subsystem": "com.yourapp.agent",
  "category": "auto",
  "event_type": "network_request",
  "session_id": "...",
  "trace_id": "trace_abc",
  "agent_auto": true,
  "message": "GET /orders -> 200",
  "env": "prod",
  "payload": {
    "method": "GET",
    "host": "api.example.com",
    "path": "/orders",
    "status": 200,
    "duration_ms": 128
  }
}
```

## Acceptance Criteria（可测验收条件）

> 每条都应是「测试能验证」的断言，而非形容词。

- [ ] `SchemaTests`：任一 `emit` 产出行的顶层键 ⊆ {ts,level,service,event_type,session_id,agent_auto,message, trace_id,subsystem,category,env,user_id,payload}，且 7 个必填键齐全。
- [ ] `SchemaTests`：线格式中**不出现** `eventType/sessionId/traceId/agentAuto/timestamp` 等 camelCase/历史别名。
- [ ] `SchemaTests`：业务字段（如 `status`/`duration_ms`）只存在于 `payload`，不提升到顶层。
- [ ] `SchemaTests`：level 词表只允许 `trace|debug|info|warn|error|critical`；Kotlin 内部若用 `warning` 必须映射为 `warn`。
- [ ] `SchemaTests`：能用 `Json` 解析 canonical 的 `example.json` 等价串并还原 `event_type`/`session_id`/`agent_auto`/`payload`。
- [ ] `LoggerTests`：`child(ctx)` 返回的实例合并 `session_id/user_id/subsystem/env` 等作用域，且不污染原实例。
- [ ] `LoggerTests`：`setLevel(level)` 后，低于该级别的手动日志被丢弃，自动埋点事件（框架核心价值）始终记录。
- [ ] `LoggerTests`：`redact(paths)` **追加**脱敏路径；默认脱敏键不可关闭。
- [ ] `RedactorTests`：命中敏感 key（不区分大小写、忽略 `_-` 分隔）整体掩码；自由文本中 `Authorization: Bearer xxx` 被正则脱敏；对象/数组递归脱敏。
- [ ] `LoggerTests`：`emit` 写出合法单行 JSONL 到文件（线程安全），可被逐行解析。
- [ ] `ConfigTests`：能从与 Web/macOS 共用的 `config/logging.config.json` 解析出 `level/service/env/redactPaths`，且 redactPaths 默认键不可减（只能追加）。
- [ ] `AndroidInstrumentationTests`（android 模块）：`bootstrap` 后页面跳转产生 `screen_view`；未捕获异常产生 `crash`（`agent_auto:true`）；主线程阻塞 >250ms 产生 `hang`；OkHttp 请求产生 `network_request` 且出站请求被注入 `traceparent`。
- [ ] 全部门禁：`agentlog-core` 通过 `./gradlew test`（JVM，无需 Android）；`agentlog-android` 可在 AGP 下 `assemble`/`compile`。

## Done when（完成定义）

- 所有验收测试通过（core 在 JVM 全绿；android 模块可编译）；边界（网络不记 body、脱敏不可关、字段集封闭）覆盖；`docs/specs/android-logging/*` 与本特性 README 已更新；`trace_id` 已贯穿网络链路。
