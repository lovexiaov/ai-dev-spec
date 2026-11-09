# HANDOFF: 日志数据契约完备性（log-data-contract）

> 连续性凭证：每个特性一份，每次收工更新。新 Agent 启动第一件事就是读它。
> 上游：`spec.md`（契约）、`plan.md`（已人工批准）、`tasks.md`（逐项状态与证据）。

## Goal（本次目标）

- **做完的判定**：六端（Python / Go / Java / Android / Web / macOS）都能写出 Schema v1.3 的
  `release` 与统一异常词表，OTLP 侧映射出 `service.version` / `exception.*`；六端测试与
  `xlang_verify.py` 全绿；文档与实现一致。
- **绝不能改的东西**：只加可选字段（v1.2 行必须仍然合法）；不改 `trace_id` / `span_id` 语义；
  不做 Sentry/APM 集成；不做崩溃落盘（方案 A：落盘/重放交宿主 sink）；不引入第三方依赖。

## Current State（当前状态）

- Branch: `main`（六子仓 + monorepo 均在 main，无 detached HEAD）
- 进度：T1–T10 全部 `done`（证据见 `tasks.md`）；T11 已本地提交六子仓 + monorepo，待 CI 确认。
- 测试（本机实测）：

| 端      | 命令                                                       | 结果                             |
| ------- | ---------------------------------------------------------- | -------------------------------- |
| Python  | `python3 -m unittest discover -s tests -q`                 | 108 tests OK                     |
| Go      | `go test ./...`                                            | ok                               |
| Java    | `mvn -q test`                                              | 113 tests / 0 failures           |
| Android | `./gradlew :agentlog-core:test :agentlog-core:ktlintCheck` | BUILD SUCCESSFUL                 |
| Web     | `pnpm test`                                                | 60 passed（39 otlp + 21 logger） |
| macOS   | 本地 XCTest 桩（`/tmp/swiftrun`，见下）                    | 64 passed / 0 failed             |
| 跨端    | `python3 tools/otlp-compat-verify/xlang_verify.py`         | 退出码 0，5/5 端一致（7 条样例） |
| 适配性  | `python3 tools/otlp-compat-verify/validate.py`             | ALL PASS                         |

## What Changed（已改动）

### 契约与配置（monorepo）

- `docs/logging-framework/schema/log-event.schema.json`：`version` → `1.3.0`，新增可选 `release`
  （`string`，`maxLength: 128`）；`required` 未变。
- `docs/logging-framework/schema/example.json`：修正为 32 位 hex id（原 `trace_...` 非法），补 `release`。
- `docs/logging-framework/schema/example-crash.json`（new）：带 `release` + 标准异常词表的 crash 样例。
- 5 份 schema 副本同步（python / go / java / android 的 `docs/schema/` + `templates/base/docs/...`），
  `diff` 全部一致（含新增 `example-crash.json`）。
- `config/logging.config.{schema.json,json,ts}` + `templates/base/config/*`：新增 `release?`。
- 文档：`INTERFACE.md` 新增 §4「异常与版本」；`README.md` §3.1/§3.4/§3.5/§7；`OTLP-MAPPING.md` §3/§10.1。
  `templates/base/docs/logging-framework/INTERFACE.md` 原本落后一版（缺 v1.2 追踪模型段），已重新同步。

### 六端源码（每端同一套落点）

- 事件模型加 `release`（边界校验：非空 + ≤128，否则不写键）。
- Config 加 `release`；Logger 在**唯一写入入口**盖章；`child()` 继承。
- 崩溃/异常采集点按标准词表写 `payload`：`exception` / `exception_message` / `stack` / `mechanism`。
- OTLP 适配器：`release` → resource `service.version`（顺序：`service.name` → `deployment.environment`
  → `service.version` → `session.id` → `telemetry.*`）。
- 各端 `CHANGELOG.md` 加 `[Unreleased]` 段；`README.md` 补 `release` 与词表说明。
- 端特有兜底保留：macOS `raw`、Web `componentStack`、Python `thread`。

### 一致性工具

- `xlang/samples.json`：样例 6 → 7 条（+1 条带 `release` 与标准异常词表的 crash；2 条加 `release`）。
- `xlang/harness/Dump.kt`、`main.swift`：映射补 `release`（其余四端直接吃原始 dict，无需改）。
- `validate.py`：resource 映射补 `service.version`，并加断言 4.8。

## Commands Run & Results（已跑命令与结果）

```bash
# 六端（见上表）
cd logging-framework/python/AgentLog && python3 -m unittest discover -s tests -q   # 108 OK
cd logging-framework/go/AgentLog && go test ./...                                  # ok
cd logging-framework/java/AgentLog && mvn -q test                                  # 113 / 0
cd logging-framework/android/AgentLog && ANDROID_HOME=~/Library/Android/sdk \
    ./gradlew :agentlog-core:test :agentlog-core:ktlintCheck                       # BUILD SUCCESSFUL
cd logging-framework/web/Observability && pnpm test                                # 60 passed

# macOS（本机 swift build 被 sandbox-exec 拒绝，用替身模块跑）
# /tmp/logging-shim（Logging 替身）+ /tmp/kscrash-shim（KSCrashInstallations 替身）+ /tmp/swiftrun（XCTest 桩）
cd /tmp/swiftrun && swiftc -swift-version 5 -o run shim.swift xctest-runner.swift src/*.swift \
    tests/*.swift main.swift -I /tmp/logging-shim -I /tmp/kscrash-shim \
    -L /tmp/logging-shim -L /tmp/kscrash-shim -lLogging -lKSCrashInstallations
DYLD_LIBRARY_PATH=/tmp/logging-shim:/tmp/kscrash-shim ./run                        # passed=64 failed=0

# 跨端一致性
python3 tools/otlp-compat-verify/xlang_verify.py                                   # exit 0
python3 tools/otlp-compat-verify/validate.py                                       # ALL PASS
```

> macOS 复跑提示：`gen.py` 会按 `func testXxx()` 自动生成 runner；`python3 gen.py InstrumentationTests`
> 可跳过依赖真实 KSCrash 的 `InstrumentationTests`（本地替身下它必然失败，因为 `reportUserException` 是空实现）。

## Decisions & Why（决策与理由）

- **`release` 放顶层而非 payload**：下游要按版本过滤/聚合，且 OTLP 有标准映射 `service.version`。
- **盖章收口在 logger 唯一入口**：避免"某条路径忘了盖章"。例外是崩溃事件——macOS 的
  `CrashReporter` 直接构造 `AgentLogEntry`（不经过 `record()`），因此 `release` 显式下传；
  Python/Go/Java/Android 的 crash 走 `record_auto` 同一入口，无需特殊处理。
- **不校验 `release` 格式**：版本来源多样（semver / git sha / build no.），只限长度防注入。
- **payload 词表靠"文档 + 测试"约束，不收紧 schema**：schema 的 `payload` 保持
  `additionalProperties: true`，否则 v1.2 历史行会被判非法。
- **`stack` 保持单字符串**：不引入解析器（零依赖），下游要帧级自己解析。
- **macOS 解析 best-effort**：KSCrash 报告结构随版本演进，只认明确存在的键；同时兼容
  `crash.error.user_reported` 与 `user.user_exception` 两种形态、`backtrace` 与 `contents` 两种帧数组。
  解析失败不抛错，`raw` 兜底——**崩溃事件的完整性优先于字段完备**。

## Next Steps（下一步）

1. 推六子仓 → 观察各自 CI；再推 monorepo（pre-push 会跑 gate-runner 全量）→ 观察 CI。
2. CI 若在 macOS `InstrumentationTests.testCrashReportRecorded` 上失败（真实 KSCrash 报告结构与
   假设不符），按实际报告调整 `CrashReporter.standardPayload` 的取键路径；**不要为了让它过而弱化
   断言**（`mechanism == reported`、`exception` 非空、`raw` 存在这三条是关键契约）。
3. 发布决策（未做）：本轮未升 SDK 版本号，CHANGELOG 记在 `[Unreleased]`。若要发版，六端同步
   `1.3.0` + 打 tag——注意 `telemetry.sdk.version` 六端必须一致，否则 `xlang_verify` 会报差异
   （该键未在忽略列表里，只有 `telemetry.sdk.language` 被忽略）。

## Blockers / Open Questions（阻塞与待解）

- macOS 的 `InstrumentationTests` 只能在 CI 跑（本机 SPM 被 sandbox-exec 拒绝）。
- `docs/specs/log-data-contract/spec.md` 的 3 个 Open Questions 已在 `plan.md` 定稿
  （release 不校验格式 / `mechanism` 保留 `reported` / `ai_error` 纳入词表），无需再议。

## How to Verify（如何验证）

```bash
# 契约层
python3 -c "import json;json.load(open('docs/logging-framework/schema/log-event.schema.json'))"
for d in python/AgentLog go/AgentLog java/AgentLog android/AgentLog; do
  diff -q docs/logging-framework/schema/log-event.schema.json logging-framework/$d/docs/schema/log-event.schema.json
done

# 六端 + 一致性（命令见上）
python3 tools/otlp-compat-verify/xlang_verify.py && python3 tools/otlp-compat-verify/validate.py

# monorepo 门禁
node tooling/gate-runner.mjs
```
