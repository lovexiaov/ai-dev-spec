# 面向 Agent 的统一日志框架 · 通用接入规范（语言无关）

> **状态（2026-11-07）**：**Schema v1 已冻结**，各端实现均已抽为独立仓库、以 submodule 挂入并通过测试：Web `logging-framework/web/Observability`（[`agent-log-web`](https://github.com/lovexiaov/agent-log-web)）、macOS `logging-framework/macos/AgentLog`（`agent-log-macos`）、Android `logging-framework/android/AgentLog`（[`agent-log-android`](https://github.com/lovexiaov/agent-log-android)）、Java `logging-framework/java/AgentLog`（[`agent-log-java`](https://github.com/lovexiaov/agent-log-java)）、Go `logging-framework/go/AgentLog`（[`agent-log-go`](https://github.com/lovexiaov/agent-log-go)）、Python `logging-framework/python/AgentLog`（[`agent-log-python`](https://github.com/lovexiaov/agent-log-python)）。
> 平台专属实现与完整设计以子模块 `logging-framework/macos/AgentLog/Docs/macos-agent-logging-design.md` 为**真源**。
> 本文件只沉淀**通用、语言无关**的约束，供所有端（Web / macOS / 服务端 / 其他）共同遵守。

## 1. 目标

为多个项目建立**统一、面向 Agent（AI 调试/排障）**的日志接入规范，使 Agent 能像人一样"读日志排障"，而不是每个项目各搞一套。

## 2. 通用约束（所有端必须遵守）

- **C1 遵守 Schema v1**：每一条事件都是单行 JSON（JSONL），字段严格遵循 [`schema/log-event.schema.json`](./schema/log-event.schema.json)（字段表见 §3）。**顶层不允许扩展**——非保留字段一律进 `payload`。
- **C2 线格式唯一，命名不留方言**：字段名在所有端**逐字相同**（snake_case）。语言内部命名（TS `camelCase`、Swift 属性名）可自由，但**只在序列化边界做映射**，不得把内部命名漏到线上。历史上 `event ↔ event_type`、`timestamp ↔ ts` 这类"对应关系"已废止——不存在别名，只有同一个字段名。
- **C3 本地优先 & 易导出**：本地持久化 + 一键导出 JSONL；Agent 可直接消费；默认不引入后端/云端依赖（轻量优先）。
- **C4 业务零改造接入**：薄封装统一 API，一处初始化；自动埋点默认全开，业务侧不写任何埋点代码。
- **C5 自动埋点默认全开（可关闭）**：覆盖 UI 交互/页面浏览、网络请求、崩溃/未捕获异常、性能/卡顿四类信号；自动事件统一标记 `agent_auto: true` 与明确 `event_type`，Agent 可一键筛选"机器视角时间线"。
- **C6 强制脱敏**：在 logger 层（而非调用方）强制脱敏；默认脱敏键 `password / token / authorization / cookie / secret`（各端可加不可减，需覆盖 `api_key`、`access_token` 等带分隔符变体）；网络默认只记 `host/path/status/耗时/error`，不记 query 敏感参数与 body。
- **C7 验收门槛**：日志必须可被 Agent 程序化消费（结构化、机器可读、可按 `event_type` 过滤），并纳入 spec 验收条件。**两端必须各有一条测试断言输出字段集与 schema 一致**，否则规范会随时间腐化。

## 3. Schema v1（唯一线格式）

机器可校验版本：[`schema/log-event.schema.json`](./schema/log-event.schema.json)；参考样例：[`schema/example.json`](./schema/example.json)。

### 3.1 字段表

| 字段         | 必填 | 类型   | 说明                                         |
| ------------ | ---- | ------ | -------------------------------------------- |
| `ts`         | ✅   | string | 事件时间，RFC3339 / ISO8601                  |
| `level`      | ✅   | enum   | 见 §3.2 词表                                 |
| `service`    | ✅   | string | 服务 / App 标识                              |
| `event_type` | ✅   | string | 语义事件名（snake_case）；普通日志固定 `log` |
| `session_id` | ✅   | string | 一次运行 / 会话标识                          |
| `agent_auto` | ✅   | bool   | `true` = 框架自动埋点                        |
| `message`    | ✅   | string | 人可读摘要（已脱敏）                         |
| `trace_id`   | ❌   | string | 跨端追踪串联，与 `traceparent` 同源          |
| `subsystem`  | ❌   | string | 子系统，通常为反向域名                       |
| `category`   | ❌   | string | 业务分类                                     |
| `env`        | ❌   | string | dev / staging / prod                         |
| `user_id`    | ❌   | string | 内部用户 id（禁止直接个人信息）              |
| `payload`    | ❌   | object | 事件专属上下文（已脱敏）                     |

### 3.2 level 词表

`trace` < `debug` < `info` < `warn` < `error` < `critical`

- 写入端只允许这 6 个值，**必须写 `warn`**。
- `warning` 仅为**读取端兼容别名**（历史日志 / syslog 习惯），聚合器读到需归一化为 `warn`；写入端禁止产出。

### 3.3 扩展规则

- 顶层字段集**封闭**（schema 中 `additionalProperties: false`）。新增字段 = 升 schema 版本，禁止各端私加。
- 业务自定义字段一律进 `payload`，键名 snake_case。

### 3.4 内部命名 ↔ 线格式映射

语言内部命名自由，映射只在序列化边界发生：

| 概念     | 线格式（所有端一致） | TS 内部（authoring） | Swift 内部（属性名） |
| -------- | -------------------- | -------------------- | -------------------- |
| 时间     | `ts`                 | `LogEvent.ts`        | `AgentLogEntry.ts`   |
| 事件名   | `event_type`         | `extra.event`        | `eventType`          |
| 会话     | `session_id`         | `extra.sessionId`    | `sessionId`          |
| 追踪     | `trace_id`           | `extra.traceId`      | `traceId`            |
| 自动埋点 | `agent_auto`         | `extra.agentAuto`    | `agentAuto`          |
| 上下文   | `payload`            | 其余 `extra` 键      | `payload`            |

> Java / Go / Python 端同样沿用「内部 camelCase → 序列化边界 snake_case」的映射，线格式与其他端逐字一致（字段名、6 档 level、封闭顶层）。

## 4. 已确认假设（通用部分）

- 汇聚方式：本地持久化 + 易导出，纯本地、无云端依赖（轻量优先）。
- 交付形态：薄封装（如 `AgentLog`），底层引擎可插拔，不锁死选型。
- 自动埋点：默认全开，按需可逐项关闭。

## 5. 平台专属实现归属（真源在外仓）

- **macOS（原生 AppKit）**：完整设计与可运行代码见子模块 `logging-framework/macos/AgentLog`（真源文档 `Docs/macos-agent-logging-design.md`）。
- **Web / 服务端**：完整实现见子模块 `logging-framework/web/Observability`（包名 `@scaffold/observability`），`LogEvent` 即线格式（§3）。
- **Android（Kotlin）**：实现已抽为独立仓库并以 submodule 挂入 `logging-framework/android/AgentLog`，真源仓库 [`agent-log-android`](https://github.com/lovexiaov/agent-log-android)（含 `agentlog-core` 纯 JVM 核心 + `agentlog-android` AGP 胶水库，详见该仓库 `README.md`）。与 macos/web 完全对齐：线格式与 §3 Schema 逐字相同；门禁契约由 `ai-dev-spec` 的 `tooling/adapters/kotlin.mjs` 适配器 + 核心模块内 `.toolchain.json` 驱动。独立仓库内可经 Gradle wrapper 单独编译、跑 `SchemaTests` 门禁。
- **Java（JVM 服务端 / 库）**：实现见子模块 `logging-framework/java/AgentLog`，真源仓库 [`agent-log-java`](https://github.com/lovexiaov/agent-log-java)。Maven 工程、**零运行时依赖**（手写 JSON 序列化/解析，不用 Jackson/Gson），JDK 17；`mvn test` 跑 `SchemaTests`（C7 字段集断言）门禁，`checkstyle` 为风格门禁。
- **Go（服务端）**：实现见子模块 `logging-framework/go/AgentLog`，真源仓库 [`agent-log-go`](https://github.com/lovexiaov/agent-log-go)。**仅标准库**（零第三方依赖），`go test ./...` 跑 `TestSchemaConformance`（C7）门禁；内置 `HTTPMiddleware`（network_request）与 `InstallPanicHandler`（crash）自动埋点；`gofmt` / `go vet` 为门禁。
- **Python（服务端 / 脚本）**：实现见子模块 `logging-framework/python/AgentLog`，真源仓库 [`agent-log-python`](https://github.com/lovexiaov/agent-log-python)。**仅标准库**（`unittest`，不依赖 pytest / jsonschema），`python3 -m unittest discover -s tests` 跑 `SchemaTests`（C7）门禁；含 `install_crash_handler()` 自动埋点。
- **其他端**：遵循 §2 通用约束与 §3 Schema，平台细节自维护，不在本脚手架重复。

## 6. 与 ai-dev-spec 的一致性

- 字段、脱敏策略、trace 串联、结构化输出四原则贯通所有端。
- 禁止业务直连底层日志库；统一经薄封装接入，避免"每端一套日志方言"。
- 新增端接入时，必须先通过 §2 C7 的字段集断言测试，再谈功能。

## 7. OTel / OTLP 对齐（D3）

Schema v1 是**事件源**格式，OTel/OTLP 是**传输与后端**标准，二者互补而非替代。映射规范真源见 [`OTLP-MAPPING.md`](./OTLP-MAPPING.md)：

- 每条事件 → 一条 OTLP `LogRecord`；
- `network_request` / `db_query` → 额外一条 `SPAN_KIND_CLIENT` Span（HTTP / Database 语义约定）；
- `critical` → `FATAL`(21)；`payload.*` 展平为 `payload.<k>` 属性；
- `traceId`/`spanId` 由 SHA-256 **确定性派生**（Schema 无 `span_id`，且重试需幂等）。

首个实现：Python `agentlog/otlp.py`（`to_otlp` / `OTLPSink`，仅标准库），其余端待跟进。
