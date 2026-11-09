# Spec: 日志数据契约完备性（log-data-contract）

> 复制 `docs/specs/_template` 为 `docs/specs/log-data-contract/` 后填写。  
> 这是 Agent 的「契约与唯一事实来源」，必须**可测**、**正向定义**为主。  
> 上游真源：语言中立契约 `docs/logging-framework/INTERFACE.md` + 线格式 `docs/logging-framework/schema/log-event.schema.json` + 通用约束 `docs/logging-framework/README.md`（C1–C7）。  
> 定位：框架只做「数据生产者」——本特性只补数据的**齐全**与**一致**，**不做**任何上报 / APM 集成（Sentry / Datadog / 自研后端的消费逻辑属于下游）。

## Goal（目标）

- 让六端（Python / Go / Java / Android / Web / macOS）在「**崩溃/异常**」与「**发布版本**」两类数据上产出**齐全且逐字一致**的结构化字段，使任何下游（Sentry / Datadog / 自研收集器）无需按端特判即可消费。
- 成功长什么样：同一次异常在六端产出相同的 `exception` / `mechanism` / `release` 键与语义；配置了 `release` 时每条事件自动携带版本，未配置时行为与 v1.2 完全一致。

## Non-goals（非目标）

- **不做** Sentry / Datadog / 任何 APM 的接入、转发或 SDK 依赖——"具体怎么用"是下游自己的逻辑。
- **不做**崩溃落盘 / 离线补发：崩溃持久化与重放**交宿主 sink**（本 spec 取方案 A）。框架只产出结构化 `crash` 事件，是否落盘、落到哪由宿主决定。
- **不做** breadcrumb 环形缓冲：有序事件流本身即时间序上下文，下游自行截取窗口。
- **不把** `stack` 结构化为 frames（本期只保证单个字符串 `stack`，帧级解析交下游）。
- **不改** `trace_id` / `span_id` 语义（v1.2 已定，见 MEMORY/README）。
- **不引入**任何第三方依赖（异常归一与版本盖章必须用各端标准库实现）。

## Constraints（约束）

- **C1 遵守线格式**：顶层 `additionalProperties:false`；本次只允许**向后兼容新增可选字段** → schema `1.2.0 → 1.3.0`，不新增必填项。
- **C2 snake_case 唯一**：顶层键与 payload 标准词表全端逐字一致；内部命名自由，只在序列化边界映射，禁止 camelCase 漏到线上。
- **C3 脱敏不变**：`exception` / `exception_message` / `stack` 等文本同样经既有脱敏（C6），确保不泄露 PII / 密钥 / token。
- **C4 零依赖**：不引 SDK；语言内置能力（如 Python `traceback`、Java `Throwable#getMessage`）即可满足。
- **C5 可选语义**：`release` 缺省时**不写该键**（v1.2 行仍合法）；payload 新增键均为可选，旧下游不受影响。
- **C6 schema 副本同步**：主副本 `docs/logging-framework/schema/log-event.schema.json` 改后，必须 `cp` 同步到 `logging-framework/{go,python,java,android}/docs/schema/` 与 `templates/base/`（web/macos 无副本）。
- **C7 验收门槛**：六端 `SchemaTests` 覆盖新字段；`tools/otlp-compat-verify` 新增样例并纳入一致性比对。

## Interfaces（接口 / 数据契约）

### 新增顶层可选字段：`release`

```json
{ "release": "1.4.2+sha.9f3c1a" }
```

- `release`：string，≤128，代表发布标识（semver / git sha / build number 均可）。
- 来源：`LoggingConfig.release`，在 **emit 时盖章**（一次配置、全事件携带），不接受单条调用点覆盖。
- OTLP 映射：`resource` 属性 `service.version` = `release`（`service.name` 已由 `service` 提供）。
- 缺省 = 不写键，行为等同 v1.2。

### 异常 / 崩溃 payload 标准词表

适用于 `event_type ∈ { crash, error, ai_error }`：

```json
"payload": {
  "exception": "java.lang.NullPointerException",
  "exception_message": "Attempt to invoke ... on a null object reference",
  "stack": "java.lang.NullPointerException\n\tat com.yourapp...",
  "mechanism": "uncaught"
}
```

| 键                  | 类型   | 说明                                                                                                   |
| ------------------- | ------ | ------------------------------------------------------------------------------------------------------ |
| `exception`         | string | 异常类型/类名。Py 异常类名、Java/Kotlin 全限定类名、Go panic 值字符串、JS `error.name`、Swift 异常名。 |
| `exception_message` | string | 异常自身消息（与顶层 `message` 区分：后者是事件叙述）。不可得时省略。                                  |
| `stack`             | string | 完整堆栈/traceback 文本；不可得时省略该键。                                                            |
| `mechanism`         | enum   | `uncaught`                                                                                             | `handled` | `reported`。未捕获→`uncaught`；主动捕获/处理→`handled`；宿主显式上报→`reported`。 |

- 端特有字段（Python `thread`、Web `componentStack`、macOS `raw`）**允许保留**，但不得替代上述标准键。
- `payload` 在 schema 中仍是 `additionalProperties:true`，本词表是**文档级 + 测试级**约束（不收紧 schema 以免破坏向后兼容）。

### 各端归一要求

- **Go / Python / Java / Android**：已产出 `exception` / `stack`，需补 `mechanism`（现有 `crash` 事件为 `uncaught`），并把异常自身消息放入 `exception_message`（Python `str(exc)`、Java `throwable.getMessage()`、Go `%v`、Android `throwable.message`）。
- **macOS**：从 KSCrash `raw` **尽力解析**出 `exception` / `stack` / `mechanism`，`raw` 作为兜底保留（解析失败时仍符合"标准键可缺省"）。
- **Web**：`ErrorBoundary` 补 `exception`（`error.name`）与 `mechanism`，保留 `stack` / `componentStack`。

### 配置

```json
{ "release": "1.4.2", "sentry": { "enabled": false } }
```

- `LoggingConfig.release?`：string，可选；`config/logging.config.schema.json` 同步允许该键。
- 各端 `ConfigTests` 解析时缺省不报错、不写 `release` 键。

## Acceptance Criteria（可测验收条件）

> 每条都应是「测试能验证」的断言，而非形容词。

- [ ] 六端 `SchemaTests`：构造一次异常事件，输出必含 `exception`(string) 与 `mechanism` ∈ {`uncaught`,`handled`,`reported`}；有堆栈时含 `stack`(string)。
- [ ] 六端 `SchemaTests`：配置 `release` 后，每条事件（含自动事件）顶层带 `release` 且值等于配置；未配置时输出中**无** `release` 键。
- [ ] 六端 `SchemaTests`：v1.2 合法行在 v1.3 校验下仍合法（向后兼容）；顶层键集合 = 旧集合 ∪ {`release`}。
- [ ] `tools/otlp-compat-verify/xlang_verify.py` 新增一条异常样例：六端 `release` / `exception` / `mechanism` 逐字一致（`stack` 文本允许因运行时不同而不比）。
- [ ] macOS 单测：喂入一份 KSCrash 样报，产出含归一 `exception` / `stack`，且 `raw` 仍在。
- [ ] Web 单测：`ErrorBoundary` 捕获的错误事件含 `exception` 与 `mechanism`。
- [ ] 配置测试：`release` 为可选；非法类型被 config schema 拒绝；六端解析缺省不报错。
- [ ] 回归：六端现有全部测试仍绿；`docs/logging-framework/schema/example.json` 增加 `release` + 一条异常样例。
- [ ] 文档：`INTERFACE.md` 新增「异常与版本」节；`README.md` §3.5 payload 标准词表补上述四键；`OTLP-MAPPING.md` 补 `release → service.version`。

## Done when（完成定义）

- 全部验收通过；schema 升至 `1.3.0` 且 4 端副本 + `templates/base` 已同步；六端 CI 全绿；`xlang_verify.py` 全绿；
- 本 spec 与 `INTERFACE.md` / `README.md` §3.5 / `OTLP-MAPPING.md` / `example.json` 已更新；
- 明确记录：崩溃落盘**非目标**（方案 A，交宿主 sink）。

## Open Questions（待决策）

- `release` 是否做格式校验？（建议：不校验，自由字符串，仅限 ≤128）
- `mechanism` 是否保留 `reported`？（建议保留：成本低，且宿主主动上报场景真实存在）
- `ai_error` 是否同样纳入本词表？（建议纳入：Web 已有 `ai-events`，语义一致）
