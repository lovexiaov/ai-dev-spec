# Plan: 日志数据契约完备性（log-data-contract）

> 只写「本次实现真正会用到的设计决策」，不要写成论文、不要重复 AGENTS.md/CLAUDE.md 已有的全局约束。
> 上游契约：本特性 `spec.md` + `docs/logging-framework/INTERFACE.md` + `schema/log-event.schema.json`。
> 硬约束：**仅新增可选字段，schema 1.2.0 → 1.3.0，不破坏 v1.2 行**；框架不做任何上报/APM 集成；崩溃落盘交宿主（方案 A）。

## 模块边界

### 契约与配置（先行，全端依赖）

- **改** `docs/logging-framework/schema/log-event.schema.json`：新增可选顶层 `release`（string，≤128）；`version` 升 `1.3.0`；`required` 不变。
- **改** `docs/logging-framework/schema/example.json`：补一条带 `release` + 异常 payload 的样例。
- **同步副本**（主副本改后 `cp`）：`logging-framework/{go,python,java,android}/AgentLog/docs/schema/log-event.schema.json` + `templates/base/docs/logging-framework/schema/log-event.schema.json`（共 5 份）。
- **改** 配置三件套：`config/logging.config.schema.json`（加 `release?: string`）、`config/logging.config.json`、`config/logging.config.ts`；`templates/base/config/logging.config.{json,schema.json}` 同步。

### 六端源码（每端同一套落点：事件模型 / Logger / Config / OTLP / 异常归一 / 测试）

| 端      | 事件模型                         | Logger（release 盖章）            | Config                               | OTLP（service.version）             | 异常归一                                                               |
| ------- | -------------------------------- | --------------------------------- | ------------------------------------ | ----------------------------------- | ---------------------------------------------------------------------- |
| Python  | `agentlog/logevent.py`           | `agentlog/logger.py`              | `agentlog/config.py`                 | `agentlog/otlp.py`                  | `agentlog/coretypes.py`（`install_crash_handler`）                     |
| Go      | `agentlog/logevent.go`           | `agentlog/logger.go`              | `agentlog/config.go`                 | `agentlog/otlp.go`                  | `agentlog/event.go`（`InstallPanicHandler`）                           |
| Java    | `LogEvent.java`                  | `Logger.java`                     | `LoggingConfig.java`                 | `OtlpMapper.java`                   | `CoreTypes.java`（`installCrashHandler`）                              |
| Android | `agentlog-core/.../LogEvent.kt`  | `agentlog-core/.../Logger.kt`     | `agentlog-core/.../LoggingConfig.kt` | `agentlog-core/.../OtlpMapper.kt`   | `agentlog-android/.../AgentLogAndroid.kt`                              |
| Web     | `web/Observability/src/types.ts` | `src/logger.ts`                   | `src/index.ts`（config 类型）        | `src/otlp.ts`                       | `src/frontend/index.tsx`（ErrorBoundary）+ `src/frontend/ai-events.ts` |
| macOS   | `Sources/AgentLog/Model.swift`   | `Sources/AgentLog/AgentLog.swift` | `AgentLogConfig`（同前）             | `Sources/AgentLog/OtlpMapper.swift` | `Sources/AgentLog/CrashReporter.swift`（KSCrash raw 解析）             |

- 文档：`docs/logging-framework/{INTERFACE.md, README.md §3.5, OTLP-MAPPING.md}`；各端 `README.md` / `CHANGELOG.md` 按需。
- 一致性工具：`tools/otlp-compat-verify/xlang/samples.json` 增异常样例；六端 harness（`dump.py` / `main.go` / `XlangMain.java` / `Dump.kt` / `dump.mjs` / `main.swift`）的 sample→event 映射补 `release`。
- **不改** 根 `src/`（占位），不改 `trace_id`/`span_id` 语义。

## 数据流

```
LoggingConfig.release ──┐
                        ▼
业务 log / 自动埋点 ──► Logger.record() ──► LogEvent(+release) ──► JSON 行（顶层 release）
                                            │
                                            └──► OTLP 适配器 ──► resource.service.version
异常/崩溃 ──► payload{exception, exception_message, stack, mechanism} ──► 同一 LogEvent 管线
```

- **release 只在 Logger 统一入口盖章**：`record()` 组装 `LogEvent` 时从 config 取 `release` 写入，`child()` 继承，不依赖任何调用点；未配置则不写键。
- **异常归一发生在采集点**：各端 crash handler / ErrorBoundary 在构造 payload 时按标准词表填键；OTLP/序列化层不再二次加工。
- 自动事件（`agent_auto:true`）与手动日志走同一盖章路径，保证"每条事件都带 release"。

## 本次特有的实现选择

- **`release` 放顶层而非 payload**：下游需要按版本过滤/聚合，属一等公民；且 OTLP 有标准映射 `service.version`（`service.name` 已由 `service` 提供）。放 payload 会失去"可直接按字段查"的能力。
- **盖章在 logger、不校验格式**：版本来源多样（semver / git sha / build no.），强制格式会误伤；仅限 ≤128，防超长注入。
- **payload 词表用「文档 + 测试」约束，不收紧 schema**：`payload` 保持 `additionalProperties:true`，避免 v1.2 行被拒；一致性靠各端 `SchemaTests` + `xlang_verify` 守。
- **`stack` 保持单字符串**：不结构化 frames（spec 非目标）。下游若要帧级，自行解析；本期不引入解析器，保持零依赖。
- **macOS 归一采用 best-effort**：从 KSCrash `raw` 尽力提取 `exception`/`stack`/`mechanism`，失败则标准键缺省、`raw` 兜底——不因解析失败丢崩溃事件。
- **崩溃不落盘（方案 A）**：框架不新增文件缓冲；`crash` 事件交给宿主 sink，落盘/重放由宿主决定。文档明确写进 Non-goals，避免后续误加。

### 已定的口径（原 spec Open Questions）

- `release`：**不校验格式**，自由字符串，≤128。
- `mechanism`：**保留 `reported`**（宿主显式上报场景真实）。
- `ai_error`：**纳入**标准词表（Web 已有 `ai-events`）。

## 必须 break 的旧路径

- **无破坏性替换**，纯增量。约定：
  - 不删除 macOS 的 `raw`、Web 的 `componentStack`、Python 的 `thread` —— 作为端特有兜底与新标准键并存。
  - 不新增"兼容层 if-else"：例外是 macOS 解析时"标准键优先、raw 兜底"的明确回退，属必要降级而非历史兼容。

## 实施顺序

1. **契约先行**：schema 主副本 → `example.json` → `cp` 同步 5 份副本；config schema/json/ts + templates/base 同步。
2. **Python 作参考实现**：`LogEvent.release` → `Logger` 盖章 → `config` 解析 → `coretypes.install_crash_handler` 补 `mechanism`/`exception_message` → `otlp.py` resource `service.version`；`pytest` 全绿。
3. **其余五端对齐**（顺序：Go → Java → Android → Web → macOS，逐端"改完即跑本端全测"，避免跨端堆错）。
4. **一致性**：`xlang/samples.json` 增异常样例 + 六端 harness 补 `release` → `python3 tools/otlp-compat-verify/xlang_verify.py` 全绿。
5. **文档**：INTERFACE「异常与版本」、README §3.5、OTLP-MAPPING、各端 README/CHANGELOG。
6. **提交**：六子仓各自 commit（注意 detached HEAD，先确认在 main）→ monorepo 指针同步 → CI 全绿。

## 风险与缓解

| 风险                                                   | 缓解                                                                                                                                                       |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| schema 5 份副本漂移                                    | 主副本改后立即 `cp`；提交前 `diff` 校验 5 份一致（可加进校验脚本）                                                                                         |
| `release` 盖章遗漏某路径（自动事件 / child / 异步）    | 盖章收口在 `Logger.record()` 单一入口；单测覆盖「自动事件也带 release」「child 继承」                                                                      |
| macOS KSCrash `raw` 结构随版本变化                     | best-effort 解析 + raw 兜底 + 解析失败不抛；单测用固定样报，不依赖真实崩溃                                                                                 |
| 各端异常字段语义漂移（类名 vs 全限定 vs panic 字符串） | `exception` 定义写进 INTERFACE 词表；各端 `SchemaTests` 断言键与 `mechanism` 枚举；`xlang` 不比对 `stack` 文本、只比键与 `exception`/`mechanism`/`release` |
| 向后兼容被破坏                                         | 只加可选字段；用一份 v1.2 样例在 v1.3 校验器下跑通过                                                                                                       |
| `release` 泄露内部版本信息                             | 可选、默认不配置；README 提示按需开启                                                                                                                      |
| 六端同改、测试面大                                     | 逐端改完即跑本端全测；Python 先作基准，其余端对齐其输出                                                                                                    |

---

## ✅ Human Approval

> Agent 在获得本区块人工勾选前，**不得修改实现代码**。
> 本特性代码落点在 `logging-framework/` 六个子仓库（非根 `src/`），但涉及 schema 版本升级与六端同步，按 ASK FIRST 仍须人工批准：

- [x] 架构/设计已审阅（仅加可选 `release`、异常 payload 词表、崩溃不落盘=方案 A、schema 1.3.0 向后兼容），批准进入实现阶段（审阅人：Marco 日期：2026-11-10）
