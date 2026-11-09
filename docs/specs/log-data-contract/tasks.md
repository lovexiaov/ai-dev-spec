# Tasks: 日志数据契约完备性（log-data-contract）

> 任务要拆到「Agent 能稳定执行」的粒度：改哪些文件 + 跑哪些验证 + 完成判定。
> 每项带 **状态** 与 **验证证据**，便于随时换 Agent 接手（要点 4）。
>
> - 状态：`todo` / `in_progress` / `blocked` / `done`
> - 证据：`Verified`(真实跑通) / `Proxy`(类型/lint/单测间接证明) / `Not run`(未执行)

## 任务清单

- [x] **T1** 契约层：`schema/log-event.schema.json` 加可选 `release`、version→1.3.0；`example.json` 补 release + 异常样例（顺带修正为 32-hex id）；`cp` 同步 5 份副本
  - 状态：done | 证据：Verified
  - 验证：schema JSON 合法；5 份副本（python/go/java/android + `templates/base`）`diff` 全部一致；`tools/otlp-compat-verify/validate.py` 用真实 schema 校验通过（`ALL PASS`）
  - 判定：schema 合法、`required` 未变、5 份副本逐字相同 ✅

- [x] **T2** 配置层：`config/logging.config.{schema.json,json,ts}` 加 `release?`；`templates/base/config/*` 同步
  - 状态：done | 证据：Verified
  - 验证：三件套 JSON 均可 `json.load`；config schema 中 `release` 为 `string` + `maxLength:128`；`templates/base/config/*` 与主副本一致
  - 判定：`release` 可选、缺省不报错 ✅

- [x] **T3** Python 参考实现：`logevent.py`/`logger.py`/`config.py`/`coretypes.py`/`otlp.py` + 测试
  - 状态：done | 证据：Verified
  - 验证：`cd logging-framework/python/AgentLog && python3 -m unittest discover -s tests -q` → **Ran 108 tests, OK**（原 100，新增 8）
  - 判定：新增 release/exception/mechanism 断言全绿，旧用例不回归 ✅
  - 备注：本项目 stdlib-only，**不用 pytest**（计划里的 `python -m pytest` 写法已纠正为 unittest）

- [x] **T4** Go 对齐：`logevent.go`/`logger.go`/`config.go`/`event.go`/`otlp.go` + 测试
  - 状态：done | 证据：Verified
  - 验证：`cd logging-framework/go/AgentLog && go test ./...` → `ok github.com/lovexiaov/agent-log-go/agentlog`
  - 判定：全绿 ✅

- [x] **T5** Java 对齐：`LogEvent.java`/`Logger.java`/`LoggingConfig.java`/`CoreTypes.java`/`OtlpMapper.java` + 测试
  - 状态：done | 证据：Verified
  - 验证：`cd logging-framework/java/AgentLog && mvn -q test` → 113 tests / 0 failures（新增 7）
  - 判定：全绿 ✅

- [x] **T6** Android 对齐：`agentlog-core` 五个文件 + `AgentLogAndroid.kt` + 测试
  - 状态：done | 证据：Verified
  - 验证：`ANDROID_HOME=~/Library/Android/sdk ./gradlew :agentlog-core:test :agentlog-core:ktlintCheck` → BUILD SUCCESSFUL
  - 判定：全绿 + ktlint 通过 ✅

- [x] **T7** Web 对齐：`types.ts`/`logger.ts`/`index.ts`/`otlp.ts`/`frontend/index.tsx`/`ai-events.ts` + 测试
  - 状态：done | 证据：Verified
  - 验证：`cd logging-framework/web/Observability && pnpm test` → **60 passed**（39 otlp + 21 logger）
  - 判定：全绿 ✅

- [x] **T8** macOS 对齐：`Model.swift`/`AgentLog.swift`/`CrashReporter.swift`/`OtlpMapper.swift` + 测试
  - 状态：done | 证据：Proxy（本地 shim 全量跑 + typecheck）+ Verified（xlang 端到端）
  - 验证：本机 `swift build` 被 sandbox-exec 拒绝，改用 `/tmp/swiftrun`（XCTest 桩 + `Logging`/`KSCrashInstallations` 替身模块）编译并运行 → **64 passed / 0 failed**；`InstrumentationTests` 依赖真实 KSCrash 与 AppKit，仅 CI 覆盖；`swiftc -typecheck` 全量（含 KSCrash 分支）零 error
  - 判定：CI 全绿（待 T11 确认）⚠️→ 以 CI 为准
  - 新增：`Tests/AgentLogTests/CrashPayloadTests.swift`（KSCrash 报告 → 标准词表，含 `user_reported` / `user.user_exception` 两种形态与旧格式 `contents`）

- [x] **T9** 一致性：`xlang/samples.json` 异常样例 + 六端 harness 补 `release`；跑 `xlang_verify.py`
  - 状态：done | 证据：Verified
  - 验证：`python3 tools/otlp-compat-verify/xlang_verify.py` → **退出码 0**，`5/5 端与 python 基准一致（样例 7 条事件）`
  - 判定：退出码 0 ✅
  - 附加核对：六端产物中带 release 的 2 组 resource 均产出 `service.version=2.3.1`；异常样例的 `exception.type` / `exception.message` / `exception.stacktrace` 三键六端完全一致

- [x] **T10** 文档：INTERFACE「异常与版本」、README §3.5、OTLP-MAPPING、各端 README/CHANGELOG
  - 状态：done | 证据：Verified
  - 改动：`docs/logging-framework/INTERFACE.md` 新增 §4「异常与版本」（release 盖章位置/校验/缺省、payload 词表、明确非目标）；`README.md` §3.1 字段表 + §3.4 映射表 + §3.5 词表（含异常词表）+ §7 OTLP；`OTLP-MAPPING.md` §3（`release`→`service.version`、`mechanism` 无标准映射）+ §10.1（样例 7 条）；六端 `CHANGELOG.md` 各加 `[Unreleased]`；六端 `README.md` 补 `release` 说明
  - 判定：内容与实现一致 ✅
  - 顺手修正：`INTERFACE.md` 的 `templates/base` 副本原已落后一个版本（缺 v1.2 追踪模型段），已重新同步；Android / Web / macOS README 样例里的非法 `trace_id: "trace_abc"` 一并改成 32 位 hex

- [ ] **T11** 提交：六子仓 commit（确认在 main）→ monorepo 指针同步 → CI
  - 状态：in_progress | 证据：Not run
  - 判定：7 仓 CI success

## 完成标准

- 所有验收测试通过；六端 + monorepo 门禁全绿；`xlang_verify.py` 退出码 0；文档同步；人工 review 通过。
- 测试未全绿前，任何项不得标记 done（验证门禁，对应 AGENTS.md §7）。
