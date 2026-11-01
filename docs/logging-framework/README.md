# 面向 Agent 的统一日志框架 · 通用接入规范（语言无关）

> **状态（2026-11-01）**：框架已实现，并经 git submodule 挂入本脚手架（`logging-framework/macos/AgentLog`），已验证可从 GitHub 正常拉取。
> 平台专属实现与完整设计以子模块 `logging-framework/macos/AgentLog/Docs/macos-agent-logging-design.md` 为**真源**。
> 本文件只沉淀**通用、语言无关**的约束，供所有端（Web / macOS / 服务端 / 其他）共同遵守。

## 1. 目标
为多个项目建立**统一、面向 Agent（AI 调试/排障）**的日志接入规范，使 Agent 能像人一样"读日志排障"，而不是每个项目各搞一套。

## 2. 通用约束（所有端必须遵守）
- **C1 结构化 & 机器可读**：统一 Schema，JSON/JSONL 输出；固定字段
  `ts / level / service / subsystem / category / event_type / session_id / trace_id / agent_auto / message / payload`。
- **C2 跨端一致**：字段与 Web 端 `packages/observability` 对齐——`event_type ↔ event`、`trace_id ↔ traceId`、`session_id` 等对应，保证多端同一套日志心智模型。
- **C3 本地优先 & 易导出**：本地持久化 + 一键导出 JSONL；Agent 可直接消费；默认不引入后端/云端依赖（轻量优先）。
- **C4 业务零改造接入**：薄封装统一 API，一处初始化；自动埋点默认全开，业务侧不写任何埋点代码。
- **C5 自动埋点默认全开（可关闭）**：覆盖 UI 交互/页面浏览、网络请求、崩溃/未捕获异常、性能/卡顿四类信号；自动事件统一标记 `agent_auto: true` 与明确 `event_type`，Agent 可一键筛选"机器视角时间线"。
- **C6 强制脱敏**：在 logger 层（而非调用方）强制脱敏；默认脱敏键 `password / token / authorization / cookie / secret`；网络默认只记 `host/path/status/耗时/error`，不记 query 敏感参数与 body。
- **C7 验收门槛**：日志必须可被 Agent 程序化消费（结构化、机器可读、可按 `event_type` 过滤），并纳入 spec 验收条件。

## 3. 已确认假设（通用部分）
- 汇聚方式：本地持久化 + 易导出，纯本地、无云端依赖（轻量优先）。
- 交付形态：薄封装（如 `AgentLog`），底层引擎可插拔，不锁死选型。
- 自动埋点：默认全开，按需可逐项关闭。

## 4. 平台专属实现归属（真源在外仓）
- **macOS（原生 AppKit）**：完整设计与可运行代码见子模块 `logging-framework/macos/AgentLog`（真源文档 `Docs/macos-agent-logging-design.md`）。
- **Web / 服务端**：复用 `packages/observability` 与同一 Schema（§2.2）。
- **其他端**：遵循 §2 通用约束，平台细节自维护，不在本脚手架重复。

## 5. 与 ai-dev-spec 的一致性
- 字段、脱敏策略、trace 串联、结构化输出四原则贯通所有端。
- 禁止业务直连底层日志库；统一经薄封装接入，避免"每端一套日志方言"。
