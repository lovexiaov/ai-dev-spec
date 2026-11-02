# 面向 Agent 的统一日志框架 · 通用接入规范（语言无关）

> **状态（2026-11-02）**：**Schema v1 已冻结**，Web（`packages/observability`）与 macOS（子模块 `logging-framework/macos/AgentLog`）两端实现已对齐并通过测试。
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

## 4. 已确认假设（通用部分）

- 汇聚方式：本地持久化 + 易导出，纯本地、无云端依赖（轻量优先）。
- 交付形态：薄封装（如 `AgentLog`），底层引擎可插拔，不锁死选型。
- 自动埋点：默认全开，按需可逐项关闭。

## 5. 平台专属实现归属（真源在外仓）

- **macOS（原生 AppKit）**：完整设计与可运行代码见子模块 `logging-framework/macos/AgentLog`（真源文档 `Docs/macos-agent-logging-design.md`）。
- **Web / 服务端**：复用 `packages/observability`，`LogEvent` 即线格式（§3）。
- **其他端**：遵循 §2 通用约束与 §3 Schema，平台细节自维护，不在本脚手架重复。

## 6. 与 ai-dev-spec 的一致性

- 字段、脱敏策略、trace 串联、结构化输出四原则贯通所有端。
- 禁止业务直连底层日志库；统一经薄封装接入，避免"每端一套日志方言"。
- 新增端接入时，必须先通过 §2 C7 的字段集断言测试，再谈功能。
