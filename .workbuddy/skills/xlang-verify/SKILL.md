---
name: xlang-verify
description: 校验 ai-dev-spec 六端日志 SDK 的 OTLP 输出与 Schema 是否一致。改动 schema、OtlpMapper/适配器、新增 event_type（含 AI 交互事件）、升级版本号、提交跨端改动前使用；也用于排查 java/kotlin harness SKIP 与格式类 CI 红灯。
agent_created: true
---

# 跨端一致性校验（xlang_verify）

## 适用时机

在以下任一情况执行完整流程：改了 `schema/log-event.schema.json` 或 `INTERFACE.md`；改了任一端的
`OtlpMapper` / `otlp.ts` / 适配器；新增标准词表或事件类型；六端升版；提交跨多子仓的改动前。

## 前置事实（不要重新推断）

- 六端是 `logging-framework/{python,go,java,android,web,macos}` 六个**独立 git 子仓**，不是目录。
- 主 schema 副本只存在于 go / python / java / android 各自 `docs/schema/` 与 `templates/base/`；
  **web / macOS 没有副本**。改主副本后必须 cp 同步，否则跨端校验能过但文档与模板漂移。
- 本机跑 Android gradle 需 `ANDROID_HOME=/Users/marco/Library/Android/sdk`。
- 契约基线：`docs/logging-framework/INTERFACE.md`（§4.4 为 AI 事件标准词表）、`OTLP-MAPPING.md`。

## 执行步骤

1. **同步 schema 副本**：把主副本 cp 到 go/python/java/android 的 `docs/schema/` 与 `templates/base/`。
2. **逐端跑格式化器**（`xlang_verify` 只校验运行时、不校验格式，CI 会另红）：
   - Go：`gofmt -l .`（有输出即需 `gofmt -w`）
   - Kotlin：`./gradlew ktlintFormat` 后 `./gradlew ktlintCheck`（行长 120 超限无法自动修，需手动抽变量）
   - TS / Web：`pnpm lint`（prettier）；monorepo harness 脚本禁用 `console`，用 `process.stdout.write`
3. **Kotlin harness 的 jar**：升版后必须重跑 `./gradlew :agentlog-core:jar`。
   harness 按 `sorted(libs.glob("agentlog-core*.jar"))[-1]` 挑 jar，旧 jar 会让校验静默跑错版本。
4. **跑一致性校验**（monorepo 根）：
   ```bash
   python3 tools/otlp-compat-verify/xlang_verify.py
   ```
   9 条样例（含 2 条 AI），Python 为基准；仅容忍 int/double 的 number-model 差异，其余差异退出码 1。
   6 仓 CI 也各跑单端测试（约 115/66/61/68/70 条）。
5. **java/kotlin 显示 SKIP 时**：先查 `tools/otlp-compat-verify/xlang/harness/{XlangMain.java,Dump.kt}`
   的 import 是否为 `cn.lovexiaov.agent.log`（残留 `com.scaffold.agentlog` 会直接 SKIP），再查 jar 是否存在。
6. **提交前核对残留**：按 hunk 拆分提交后跑 `git diff`（未暂存）逐仓确认没有自己的改动漏入索引；
   同一测试函数被拆成多个 hunk 时，工作区跑绿也看不出第二处断言没进索引，只有 CI 能发现。

## 不可动摇的契约

- `trace_id` 强制 **32 位小写 hex**；非法值在写入边界丢字段、事件照写。**绝不哈希或变形用户 id**。
- OTLP **只发 LogRecord，不产 span**；协议仅 OTLP/HTTP+JSON，gRPC 不做；四端传输交宿主 HTTP 栈。
- AI 事件业务显式埋点 `agent_auto=false`；`ai_error` 纳入 `exception.*` 映射。

## 结果判定

- 退出码 0 + 六端格式化器干净 + 单端测试全绿 = 可提交。
- 任一差异先定位到具体端的 mapper，不要改基准样例去「迁就」实现。
