# Tasks: AI 交互事件（AgentLog 六端统一）

> 任务拆到「Agent 能稳定执行」的粒度：改哪些文件 + 跑哪些验证 + 完成判定。
> 状态：`todo` / `in_progress` / `blocked` / `done`；证据：`Verified` / `Proxy` / `Not run`。

## 任务清单

- [x] **T1** 契约层：Schema 升 v1.4（主副本 + go/python/java/android 副本 + templates/base 同步 `version` 与 `event_type` description）；INTERFACE.md 新增 §4.4 AI 事件段
  - 状态：done | 证据：Verified
  - 验证：主副本 `version=1.4.0`，`cp` 同步 5 副本后 grep 六副本全部一致；INTERFACE.md §4.4 已列 6 值 + 词表 + level + 不产 span
  - 判定：✅ 六副本 version 一致 = 1.4.0

- [x] **T2** Python：`agentlog/ai_events.py`（`record_ai_*` 6 函数）+ `EventType.AI_TYPES` + `__init__` 导出 + `tests/test_ai_events.py`（7 例）
  - 状态：done | 证据：Verified
  - 验证：`python3 -m unittest discover -s tests -q` → **115 tests OK**
  - 判定：✅ 标准 `event_type` / snake_case payload / `agent_auto=false`

- [x] **T3** Go：`logger.go` 的 `Record` + `RecordAI*` 6 方法（`extra map` 合并，核心字段不被覆盖）+ `event.go` 6 常量 + `agentlog.go` 门面委托 + `ai_test.go`（7 例）
  - 状态：done | 证据：Verified
  - 验证：`gofmt -w` + `go test ./...` → **ok**
  - 判定：✅ 门面与 `*Logger` 均可调用；线格式 snake_case

- [x] **T4** Java：`AiEvents.java` + `CoreTypes.EventType` 6 值 + `Logger.record(...)` + `AgentLog` 门面委托 + `AiEventsTests.java`（6 例）
  - 状态：done | 证据：Verified
  - 验证：`mvn -o test` → **66 tests / 0 failures，BUILD SUCCESS**

- [x] **T5** Android：`AiEvents.kt` + `CoreTypes.kt` 6 值 + `Logger.record(...)`（私有 `log` 改收 raw string）+ `AgentLog.bootstrap(config, sink)` + `AiEventsTests.kt`（7 例）
  - 状态：done | 证据：Verified
  - 验证：`./gradlew check --offline` → **BUILD SUCCESSFUL（128 tasks）**；`:agentlog-core:test` 61 tests / 0 failures；ktlintCheck 通过
  - 判定：✅ core 测试 + 全项目 check 全绿

- [x] **T6** Web：`ai-events.ts` 改标准词表（`emitAi` 统一盖章 level / `event` / `category:"ai"` / `agentAuto:false`）+ `types.ts` 的 `AI_EVENT_TYPES` + `package.json` 补 `./frontend/ai-events` 导出 + `ai-events.test.ts`（8 例）
  - 状态：done | 证据：Verified
  - 验证：`pnpm typecheck` / `pnpm lint` / `pnpm test`（**68 passed**）/ `pnpm build` 全通过
  - 判定：✅ 保留 `logAi*` 函数名与参数顺序；无 camelCase 别名泄漏

- [x] **T7** macOS：`AiEvents.swift`（`AgentLog` 静态扩展 6 方法）+ `Model.swift` 6 值 + `record(...)` 改显式 `agentAuto` + `recordAI(...)` 入口 + `AiEventsTests.swift`（6 例）
  - 状态：done | 证据：Verified（本地桩）/ Proxy（真实 XCTest 由 CI 兜底）
  - 验证：`swiftc -typecheck` 全 target 零 error；`/tmp/swiftrun` 桩 → **70 passed / 0 failed**（含 6 个 AI 用例）；`runall` 含 InstrumentationTests 全量编译通过
  - 判定：✅ AI 事件测试全绿；CI 首次真编译兜底

- [x] **T8** 跨语言一致性：`xlang/samples.json` 加 2 条 AI 样例（`ai_response_received` 带 token + `request_id`、`ai_error` 带异常词表）；六端 OTLP 适配器把 `ai_error` 纳入 `exception.*` 映射
  - 状态：done | 证据：Verified
  - 验证：`python3 tools/otlp-compat-verify/xlang_verify.py` → **EXIT=0，5/5 端与 Python 基准一致（9 条事件）**；逐端 traces 均只有 2 条 span（HTTP + DB），**零 AI span**；`ai_error` 产出 `exception.type/message/stacktrace`
  - 判定：✅ 六端 logs/traces 一致、均不产 span

- [x] **T9** 文档：六端 `CHANGELOG.md` 新增 `[1.4.0] - 2026-11-11` + 六端 `README.md` AI 段落（Web 附字段迁移对照）；plan 人工批准勾选、spec 验收条件勾选
  - 状态：done | 证据：Verified
  - 判定：✅ CHANGELOG 六端一致；README 含 AI 用法与不产 span 说明

- [x] **T10** 版本对齐：六端包元数据 + `SDK_VERSION`/`__version__` 升 1.4.0（同 log-data-contract 发版流程）
  - 状态：done | 证据：Verified
  - 改动：13 处版本字面量（Python `pyproject.toml` / `__version__` / `SDK_VERSION`、Go `SDKVersion`、Java `pom.xml` / `SDK_VERSION` / 测试断言、Android `build.gradle.kts` / `SDK_VERSION`、Web `package.json` / `SDK_VERSION`、macOS `sdkVersion` / 测试断言）+ 主文档状态行
  - 验证：六端 `telemetry.sdk.version` 实测全为 `1.4.0`；`xlang_verify.py` EXIT=0（9 样例）；六端测试复跑全绿（115 / ok / 66 / check / 68 / 70）
  - 判定：✅ 六端 SDK 版本 = 1.4.0，与 schema v1.4.0 对齐

- [ ] **T11** 提交 + 发版：六子仓 commit + tag `v1.4.0` + monorepo 指针更新 + 推送 + 7 仓 CI 全绿（**推送待用户确认**）
  - 状态：in_progress | 证据：Verified（本地部分）/ Not run（推送与 CI）
  - 已完成：六子仓均在 `main` 上提交 `feat(schema-v1.4): 六端统一 AI 交互事件并发布 1.4.0`，
    各打 annotated tag `v1.4.0`（已核对 `v1.4.0^{}` == HEAD）；六仓工作区干净、无残留改动；
    新 AI 源文件与测试文件均已入提交。monorepo 已更新 6 个 submodule 指针与契约文档。
  - 待办：**推送 7 仓 + tag（不可逆，需用户明确确认）** → 7 仓 CI success。
  - 判定：7 仓 CI success；远端 tag `v1.4.0` 就绪

## 完成标准

- T1–T9 全绿；T10 版本对齐；T11 提交 + tag 完成（推送需人工确认）。测试未全绿前任何项不得标记 done。

## 本机六端测试快照（T8 后复跑，含 OTLP 改动）

| 端      | 命令                                                                 | 结果                                |
| ------- | -------------------------------------------------------------------- | ----------------------------------- |
| Python  | `python3 -m unittest discover -s tests -q`                           | 115 tests OK                        |
| Go      | `go test ./...`                                                      | ok                                  |
| Java    | `mvn -o test`                                                        | 66 tests / 0 failures               |
| Android | `./gradlew :agentlog-core:test :agentlog-core:ktlintCheck --offline` | 61 tests / 0 failures + ktlint 通过 |
| Web     | `pnpm typecheck && pnpm lint && pnpm test`                           | 68 passed                           |
| macOS   | `swiftc -typecheck` + `/tmp/swiftrun`                                | 零 error / 70 passed                |
| 跨端    | `xlang_verify.py`                                                    | EXIT=0（9 样例，5/5 端一致）        |
