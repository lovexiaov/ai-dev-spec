# HANDOFF: Android Kotlin 日志框架（AgentLog for Android）

> 连续性凭证：每个特性一份，每次收工更新。新 Agent 启动第一件事就是读它。

## Goal（本次目标）

- 在 `logging-framework/android/AgentLog/` 下实现对齐 Schema v1 的 Android Kotlin 日志框架（core 纯 JVM + android 胶水 AGP 库），含强制门禁测试 `SchemaTests`。
- 绝不能改的东西：`docs/logging-framework/schema/log-event.schema.json` 字段集（顶层封闭）、`INTERFACE.md` 接口面（emit/child/setLevel/redact）、已有 `src/` 业务代码。

## Current State（当前状态）

- Branch: `feat/android-logging`（拟定） Last commit: `<待首次提交>`
- 已完成：规划文档 + core 实现 + JVM 测试 + android 胶水 + 门禁验证 —— 100%
- 测试：`(agentlog-core) ./gradlew test` → **16 passed / 0 failed**（含对齐 Swift 的 `SchemaTests`）
- 构建：`(agentlog-core) ./gradlew build` → BUILD SUCCESSFUL（jar 产出）；`(agentlog-android) ANDROID_HOME=$SDK ./gradlew build` → BUILD SUCCESSFUL（aar + lint 通过）

## What Changed（已改动）

- `docs/specs/android-logging/{spec,plan,handoff}.md`（new）：特性契约与规划。
- `tooling/adapters/kotlin.mjs`（new）：Kotlin/JVM 门禁适配器（typecheck=`compileKotlin`、test=`test`、build=`build`）。
- `logging-framework/android/AgentLog/agentlog-core/`（new）：纯 Kotlin/JVM 核心，零第三方依赖，含 `SchemaTests`。根目录 `.toolchain.json`（adapter: kotlin）+ gradle wrapper（9.8.1）。
- `logging-framework/android/AgentLog/agentlog-android/`（new）：AGP 库（AGP 8.7 / Kotlin 2.0.21），gradle wrapper（8.11）。`includeBuild("../agentlog-core")` 复用核心。
- `logging-framework/android/AgentLog/README.md`（new）：接入规范与架构。
- **已抽为独立仓库并以 submodule 挂入**：真源 `https://github.com/lovexiaov/agent-log-android`（公开）。`ai-dev-spec` 内 `logging-framework/android/AgentLog` 现为 git submodule（commit `289dcb0`），与 macos/web 对齐。独立仓库内含 `agentlog-core` + `agentlog-android` + `README.md` + `LICENSE`，可单独经 wrapper 构建验证。

## Commands Run & Results（已跑命令与结果）

```bash
# 核心：编译 + 16 测试 + jar（wrapper 9.8.1，已缓存 6s 完成）
cd logging-framework/android/AgentLog/agentlog-core && ./gradlew build --no-daemon
# ⇒ BUILD SUCCESSFUL，测试 SchemaTests/LoggerTests/RedactorTests/ConfigTests 全绿

# Android：完整 AGP 构建（wrapper 8.11，ANDROID_HOME 指向 SDK，29s）
cd logging-framework/android/AgentLog/agentlog-android && ANDROID_HOME=~/Library/Android/sdk ./gradlew build --no-daemon
# ⇒ BUILD SUCCESSFUL（assembleDebug/Release + lint 通过）

# 门禁端到端
cd ai-dev-spec && node tooling/gate-runner.mjs --modules logging-framework/android/AgentLog/agentlog-core
# ⇒ kotlin 适配器被发现并执行 compileKotlin/test/build，全绿
```

## Decisions & Why（决策与理由）

- 核心纯 JVM、零第三方依赖（手写 JSON 序列化 + 最小化解析器）：保证无 Android SDK 也能编译测试，规避拉包风险；对齐 Swift（`Codable` 内置）/TS（`JSON.stringify` 内置）"标准库即可"的思路。
- 核心/胶水分库（非 KMP）：核心与平台无关须可 JVM 验证；Android API 需 AGP 提供 android.jar。
- 网络埋点用 OkHttp Interceptor：业界标准、业务普遍；注入并串联 `traceparent`。
- 两模块版本策略不同：core 锁 Gradle 9.8.1（纯 JVM，跟新）；android 锁 Gradle 8.11（兼容 AGP 8.7）。

## Next Steps（下一步）

- 全部完成。后续可选：① 抽为独立仓库以 submodule 挂入（对齐 macos/web 做法）；② 补充 `ui_interaction`（Accessibility/触摸监听）；③ 接入 ktlint/detekt 后在 `kotlin.mjs` 补 lint 阶段。

## Blockers / Open Questions（阻塞与待解）

- `agentlog-android` 完整编译需 AGP + Android SDK（本机已具备）；CI 需配 Android 环境 + `ANDROID_HOME`。
- 抽独立仓库（submodule 挂入，对齐 macos/web）**已完成**：独立仓库 `agent-log-android` 已建并推送公开；`ai-dev-spec` 内目录已替换为 submodule。后续若独立仓库有改动，在仓库内提交后于 `ai-dev-spec` 执行 `git submodule update --remote logging-framework/android/AgentLog` 同步。

## How to Verify（如何验证）

```bash
# 首次克隆 ai-dev-spec 后拉取 submodule
git submodule update --init logging-framework/android/AgentLog
# 独立仓库内构建
cd logging-framework/android/AgentLog/agentlog-core && ./gradlew build
cd logging-framework/android/AgentLog/agentlog-android && ANDROID_HOME=~/Library/Android/sdk ./gradlew build
```
