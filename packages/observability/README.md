# @scaffold/observability

AI 主导开发范式下「看得见、追得清、可回放」的可观测底座。**零业务依赖、可独立安装**，新项目一行接入。

## 为什么需要它（要点 2）

AI 生成代码带来新的可观测挑战，尤其前端/Web 这类难单测的应用：出错时人类看不到、Agent 不会「刷新重试」。本包把结构化日志、追踪传播、前端崩溃捕获、AI 交互事件记录做成开箱即用的核心模块。

## 快速接入

```ts
import { createLogger } from "@scaffold/observability";
import { loggingConfig } from "../../config/logging.config";

const logger = createLogger({
  service: loggingConfig.service,
  env: loggingConfig.env,
  format: loggingConfig.format,
  level: loggingConfig.level,
  redactPaths: loggingConfig.redactPaths,
});
```

### 追踪串联

```ts
import {
  runWithTrace,
  traceIdFromHeaders,
  outgoingHeaders,
} from "@scaffold/observability";

app.use((req, res, next) => {
  const id = traceIdFromHeaders(req.headers);
  runWithTrace(id, () => next());
});

// 下游调用自动带上 traceId
fetch("https://downstream", { headers: outgoingHeaders() });
```

### 前端（React）

```tsx
import {
  ErrorBoundary,
  createBrowserLogger,
} from "@scaffold/observability/frontend";
import {
  logAiRequest,
  logAiResponse,
} from "@scaffold/observability/frontend/ai-events";

const logger = createBrowserLogger({
  service: "web",
  env: "production",
  endpoint: "/api/log",
});
logAiRequest(logger, { sessionId: "s1", model: "gpt-4o" }, "总结这段对话");

<ErrorBoundary logger={logger} fallback={<p>出错了</p>}>
  <App />
</ErrorBoundary>;
```

## Agent 进度可观测（要点 4）

```ts
import {
  logAgentStep,
  logAgentHandoff,
  logAgentDecision,
} from "@scaffold/observability";
logAgentStep(
  logger,
  { feature: "auth", taskId: "T2" },
  60,
  "确认 token 校验逻辑",
);
logAgentHandoff(
  logger,
  { feature: "auth" },
  "claude",
  "codex",
  "context 接近上限，交接续作",
);
logAgentDecision(
  logger,
  { feature: "auth" },
  "复用现有邮件服务",
  "避免新增依赖",
);
```

进度由此进入同一套结构化日志，配合 `docs/specs/<feature>/handoff.md` 的交接文档，满足「可观测、可跟踪、可随时换人」。

## 设计要点

- **统一 Schema（线格式唯一）**：`LogEvent` 即 [Schema v1](../../docs/logging-framework/schema/log-event.schema.json) 线格式——`ts / level / service / event_type / session_id / agent_auto / message` 必填，`trace_id / subsystem / category / env / user_id / payload` 可选，顶层封闭（非保留键一律进 `payload`）。调用侧仍写 `event / traceId / userId` 等 camelCase，由 logger 在序列化边界映射。
- **脱敏在 logger 层**：默认键（`password/token/authorization/cookie/secret/api_key/...`）不可关闭，`redactPaths` 只能追加（相对 `payload`）。
- **AI 事件五类**：`ai_request_initiated / ai_tool_call_initiated / ai_tool_call_completed / ai_response_received / ai_guardrail_triggered / ai_error`。
- **健康端点**：`liveness()` / `readiness(deps)` 交给具体框架包装为 `GET /health`、`GET /ready`。
