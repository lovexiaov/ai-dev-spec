# Plan: Android Kotlin 日志框架（AgentLog for Android）

> 只写「本次实现真正会用到的设计决策」，不要写成论文、不要重复 AGENTS.md/CLAUDE.md 已有的全局约束。

## 模块边界

- **新增** `logging-framework/android/AgentLog/agentlog-core/`：纯 Kotlin/JVM 库（仅 Kotlin 标准库，**零第三方依赖**），实现契约核心 + 逻辑 + JVM 测试。可在无 Android SDK 环境编译与测试（本机已验证 JDK/Gradle/Kotlin 齐全）。
  - `src/main/kotlin/com/scaffold/agentlog/`：`LogEvent`、`Level`、`Redactor`、`Session`、`EventType`、`AutoInstrumentationOptions`、`Logger`、`LoggingConfig`、最小化 `Json`（手写序列化 + 解析，仅覆盖 Schema v1 固定结构）。
  - `src/test/kotlin/com/scaffold/agentlog/`：`SchemaTests`、`LoggerTests`、`RedactorTests`、`ConfigTests`。
  - 根目录 `.toolchain.json` → 走 `tooling/adapters/kotlin.mjs`。
- **新增** `logging-framework/android/AgentLog/agentlog-android/`：AGP 库（`com.android.library` + `kotlin("android")`），依赖 `:agentlog-core`，提供 Android 平台胶水：`AgentLogAndroid.bootstrap(context)`、生命周期/screen_view、未捕获异常/crash、主线程卡顿/hang、OkHttp Interceptor/network_request + `traceparent` 注入。
- **新增** `tooling/adapters/kotlin.mjs`：Kotlin/JVM 门禁适配器（`typecheck`/`test`/`build` 映射为 `./gradlew` 子命令）。
- **新增/更新** `logging-framework/android/AgentLog/README.md`：接入规范（对齐 `macos/AgentLog/README.md`）。
- 不改动 `src/`、根 `package.json`、`pnpm-workspace.yaml`（android 目录不在 pnpm workspace 内，互不干扰）。

## 数据流

- 业务侧 `AgentLog.info/warn/error/...` 或自动埋点回调 → `Logger.record(...)`：先按 `minLevel` 过滤（自动事件 `force=true` 始终记录）→ 脱敏 `message`/`payload` → 组装 `LogEvent`（Kotlin camelCase）→ `LogEvent.toJsonLine()` 在**序列化边界**映射为 snake_case 线格式 → `FileSink`（线程安全 `synchronized` 写）落盘 `agent-log.jsonl`。
- `child(ctx)` 返回新 `Logger`，合并 `session_id/user_id/subsystem/env/trace_id`，不污染原实例（对齐 TS `child` 实现）。
- 网络自动埋点：OkHttp Interceptor 在出站请求注入 `traceparent`（无则生成），完成时收敛为一条 `network_request` 事件并携带 `trace_id`，实现「点击→网络→响应/错误」跨端可回溯（对齐 Swift `NetworkInstrumentation`）。

## 本次特有的实现选择

- **零依赖纯 JVM 核心**：手写 Schema v1 的 JSON 序列化（显式 snake_case，不用反射）与最小化 JSON 解析器，**不引入 kotlinx.serialization / gson**，规避网络拉包风险、保证本机可编译可测；线格式靠 `LogEvent.toJsonLine()` 显式字段顺序与 `Json.escape` 保证。Android 模块仅依赖 `androidx` 可选注解，网络埋点用 OkHttp Interceptor（业界标准，业务已普遍使用）。
- **手写 JSON 而非库**：Schema 顶层字段**封闭且固定**，手写 writer 简单且零依赖；同时实现一个足够覆盖 `config/logging.config.json` 与事件 round-trip 的解析器（对象/数组/字符串转义/数字/布尔/null），复用为 `ConfigTests`/`SchemaTests` 的 decode 能力（对齐 Swift `JSONDecoder` 往返测试）。
- **核心/胶水分离（非 KMP）**：核心为纯 JVM 库，Android 胶水为独立 AGP 库依赖它。理由：核心逻辑与平台无关、应在无 Android 下可测可验证；Android 专属 API（`ActivityLifecycleCallbacks` 等）天然需 AGP 提供 `android.jar`，分库比 KMP 更轻、门禁更可控（core 的 `test` 阶段无需 Android SDK）。
- **level 映射**：Kotlin 内部枚举用 `WARNING` 以贴合习惯，但线格式**强制写 `warn`**；解析端兼容 `warning` 历史别名（对齐 Swift `agentName` 逻辑与 Schema §3.2）。

## 必须 break 的旧路径

- 无旧实现可替换（Android 端为全新）。仅约定：业务日志统一改走 `AgentLog.*`，不再裸用 `Log.*`/`println`（接入 Checklist 引导，非强制替换既有）。

## 风险与缓解

| 风险                                                                                                                                | 缓解                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 手写 JSON 转义/序号出错                                                                                                             | `Json.escape` 单测覆盖引号/反斜杠/控制字符；`SchemaTests` 断言字段集与 key 名，而非字符串拼接细节                             |
| 自动埋点 swizzle/钩子与第三方库冲突（Android 无 runtime swizzle，靠 `ActivityLifecycleCallbacks`/Interceptor 等官方机制，冲突面小） | 统一通过 `AgentLogConfig.autoInstrumentation` 逐项关闭；网络埋点优先支持 OkHttp（业务普遍），HttpURLConnection 走可选 wrapper |
| `agentlog-android` 需 AGP + Android SDK 才能编译（本机已具备，但 CI 需配 Android 环境）                                             | core 门禁跑 JVM 测试不依赖 Android；android 模块由接入方/CI（配 AGP+SDK）编译，`assemble`/`compile` 纳入其自身 toolchain      |
| 网络埋点 async/协程路径覆盖不全                                                                                                     | 以 OkHttp Interceptor 覆盖绝大多数同步/异步 OkHttp 调用；`URLSession.data(for:)` 式盲区在 README 诚实标注                     |
| 多端规范漂移                                                                                                                        | `SchemaTests`（本端）+ Web `Schema v1` 用例 + Swift `SchemaTests` 各守各端，任一端私改字段即失败                              |

---

## ✅ Human Approval

> Agent 在获得本区块人工勾选前，**不得修改 `src/`**。
> 本特性代码落点在 `logging-framework/android/`（非 `src/`），但作为全新跨语言模块，仍建议人工审阅以下架构决策后再扩到全量实现：

- [ ] 架构/设计已审阅（核心纯 JVM + Android 胶水分库、零依赖手写 JSON、OkHttp 网络埋点），批准进入实现阶段（审阅人：____ 日期：____）
