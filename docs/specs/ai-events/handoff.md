# HANDOFF: AI 交互事件六端统一（ai-events）

> 连续性凭证：每个特性一份，每次收工更新。新 Agent 启动第一件事就是读它。
> 上游：`spec.md`（契约）、`plan.md`（已人工批准，含 D4「不产 span」决策）、`tasks.md`（逐项状态与证据）。

## Goal（本次目标）

- **做完的判定**：六端（Python / Go / Java / Android / Web / macOS）都能产出 Schema v1.4 的
  标准 AI 交互事件（6 个 `event_type` 值 + snake_case payload 词表），`xlang_verify` 含 AI
  样例且六端 OTLP 一致且**均不产 span**；SDK 版本与 schema 同步升 `1.4.0`，tag 推送、7 仓 CI 全绿。
- **绝不能改的东西**：v1.3 行必须仍然合法（只加不改）；AI 事件为**显式埋点**（`agent_auto=false`），
  不 hook 任何 LLM SDK；OTLP 层只作 log 信号，不产 `Span`（plan.md 决策 D4）；`ai_error`
  复用 v1.3 异常词表；不引入第三方依赖。

## Current State（当前状态）

- Branch: `main`（六子仓 + monorepo 均在 main，工作区干净）
- 进度：**T1–T11 全部 `done`**（证据见 `tasks.md`）。
- 提交：六子仓均 `feat(schema-v1.4): 六端统一 AI 交互事件并发布 1.4.0`（Go 额外
  `style(go): gofmt event.go`，tag 重指到修复提交）；monorepo `984bc30` + `2bbe9c2` + `e7299f6`。
- 发版：六端 annotated tag `v1.4.0` 已推送远端（仅 Git tag，未发 npm/PyPI/Release）。
- CI：**7 仓全绿**（2026-11-11 核对：六子仓 headSha 均为 v1.4.0 指向提交；monorepo
  `e7299f6` run 42863311895 success 2m34s）。此前排队的 macOS arm64 runner 已完成
  （12m38s success），Go gofmt 修复后重跑 success。

## What Changed（已改动）

### 契约层（monorepo）

- `docs/logging-framework/schema/log-event.schema.json` → `version=1.4.0`：`event_type`
  description 增补 6 个标准 AI 值；`required` 未变（纯增量，v1.3 行仍合法）。
- 5 份 schema 副本同步（python/go/java/android 的 `docs/schema/` + `templates/base/docs/`）。
- `docs/logging-framework/INTERFACE.md` 新增 §4.4 AI 事件段（6 值 + 词表 + level + 不产 span）。

### 六端源码（每端同一套落点）

- Python `agentlog/ai_events.py`（`record_ai_*` 6 函数）；Go `logger.go` `RecordAI*` 6 方法
  - `event.go` 6 常量；Java/Android `AiEvents` + `CoreTypes` 6 值 + 门面委托；
    macOS `AiEvents.swift`（`AgentLog` 静态扩展，`record(...)` 改显式 `agentAuto`）；
    Web 保留 `logAi*` 函数名、payload 字段迁移到标准词表并传 `agentAuto: false`。
- 各端 `AiEventTests`：断言 `event_type` ∈ 6 标准值、payload 无 camelCase 别名泄漏、
  `ai_error` 带异常词表且 `level=error`。
- 六端 `CHANGELOG.md` 新增 `[1.4.0] - 2026-11-11`；`README.md` 补 AI 用法（Web 附迁移对照）。

### 一致性工具与版本

- `xlang/samples.json` 9 条样例（+2 条 AI：`ai_response_received` 带 token + `request_id`、
  `ai_error` 带异常词表）；六端 OTLP 适配器把 `ai_error` 纳入 `exception.*` 映射。
- 13 处版本字面量对齐 `1.4.0`（六端 `telemetry.sdk.version` 实测一致，否则 `xlang_verify` 报差异）。

## Commands Run & Results（已跑命令与结果）

| 端      | 命令                                                                 | 结果                                     |
| ------- | -------------------------------------------------------------------- | ---------------------------------------- |
| Python  | `python3 -m unittest discover -s tests -q`                           | 115 tests OK                             |
| Go      | `go test ./...`                                                      | ok                                       |
| Java    | `mvn -o test`                                                        | 66 tests / 0 failures                    |
| Android | `./gradlew :agentlog-core:test :agentlog-core:ktlintCheck --offline` | 61 tests / 0 failures + ktlint 通过      |
| Web     | `pnpm typecheck && pnpm lint && pnpm test`                           | 68 passed                                |
| macOS   | `swiftc -typecheck` + `/tmp/swiftrun` 本地桩                         | 零 error / 70 passed（CI 真跑兜底）      |
| 跨端    | `python3 tools/otlp-compat-verify/xlang_verify.py`                   | EXIT=0（9 样例，5/5 端一致，零 AI span） |

2026-11-11 接管复核（本 Agent 实测）：

```bash
pnpm lint && pnpm typecheck && pnpm test   # 全绿（web 68 passed）
node tooling/gate-runner.mjs               # ✅ 全部门禁通过（python adapter lint+test 115 OK）
gh run list / gh run watch                 # monorepo e7299f6 CI success；六子仓 v1.4.0 全 success
```

## Decisions & Why（决策与理由）

- **不产 span（D4）**：AI 事件在 OTLP 层只作 log 信号（可挂 `span_id` 供下游组 span）。
  经会话内 `AskUserQuestion` 人工批准（2026-11-10）。
- **`agent_auto=false` + 显式埋点**：AI 事件由业务代码经便捷方法产生，区别于 crash/network
  自动埋点；框架不 hook LLM SDK（spec 非目标）。
- **Web 保留 `logAi*` 函数名**：只改 payload 字段为标准词表、明确 level、传 `agentAuto`，
  降低业务侧迁移成本；迁移对照见 Web README。
- **`request_id` 不强制生成**：由调用方传入并跨同轮事件保持一致，框架不造轮子。
- **token 计数用 int**：xlang 校验虽已容忍 int/double，但六端统一 int 消除噪声。
- **Go tag force-update 可接受**：tag 刚发布、无外部消费，gofmt 修复后重指；
  若日后有外部依赖 tag，此操作必须重新评审。

## Next Steps（下一步）

1. **发布渠道决策（未做，等产品判断）**：仅打了 Git tag；npm / PyPI / GitHub Release 均未发。
2. 下游消费侧可选工作（不在本 spec 范围）：按 `request_id` 聚合「请求→响应→工具→错误」
   轮次视图、AI 事件看板、按 `model`/`provider` 维度统计。
3. 若做 LLM SDK 自动埋点（hook OpenAI/Anthropic 等），需新开 spec——本期明确为非目标。

## Blockers / Open Questions（阻塞与待解）

- 无阻塞。spec 验收条件 7 项全部勾选（见 `spec.md` Acceptance Criteria）。

## How to Verify（如何验证）

```bash
# 契约层：六副本 version 一致 = 1.4.0
python3 -c "import json;print(json.load(open('docs/logging-framework/schema/log-event.schema.json'))['version'])"
for d in python/AgentLog go/AgentLog java/AgentLog android/AgentLog; do
  diff -q docs/logging-framework/schema/log-event.schema.json logging-framework/$d/docs/schema/log-event.schema.json
done

# 六端测试 + 跨端一致性（命令见上表）
python3 tools/otlp-compat-verify/xlang_verify.py

# monorepo 门禁
pnpm lint && pnpm typecheck && pnpm test && node tooling/gate-runner.mjs
```
