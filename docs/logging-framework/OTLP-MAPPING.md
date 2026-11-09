# agent-log → OpenTelemetry (OTLP) 映射规范

> **状态（2026-11-08，Schema v1.2.0）**：D3「OTel 对齐」规范真源。适配器 + 内置 exporter 已在
> Python（`logging-framework/python/AgentLog/agentlog/otlp.py`、`otlp_http.py`）与
> Go（`logging-framework/go/AgentLog/agentlog/otlp.go`、`otlp_http.go`）落地，
> 其余端待跟进；两端产出的 body 已逐字对齐（见 §9.3）。
> 本文件与实现**必须同步演进**：改动映射 = 同时改本文件与各端适配器 + 测试。

## 1. 定位与边界

agent-log 与 OTel 不是竞争关系，而是**两层**：

- **agent-log**：跨端统一、Agent 优先、隐私默认安全的**事件源**，线格式是 Schema v1 JSONL（封闭顶层、6 档 level、`payload` 收敛）。
- **OTel/OTLP**：观测数据的**传输/后端标准**。Collector 收到 OTLP 后可发往 Jaeger / Tempo / Loki / Grafana / Datadog 等。

因此 OTLP 适配是**单向翻译层**（export-only）：不要求业务改用 OTel SDK，也不引入 OTel SDK/Collector 依赖。统一追踪模型中，`trace_id` 为 32 位小写 hex（与 OTLP `traceId` / W3C `traceparent` 的 trace-id 同构），`span_id` 为 16 位小写 hex（与 W3C `traceparent` 的 span-id 同构）；二者均为固定长度 hex，id 策略统一见 §6。其余 OTel 概念（resource / scope / span kind 等）不进入线格式。

## 2. 总原则

1. **每条事件首先是一条 OTLP `LogRecord`**（logs 信号），这是最自然的一一对应。
2. **操作类事件额外产出一条 `Span`**（traces 信号），用于分布式链路视图：
   - `network_request` → `SPAN_KIND_CLIENT`，套 HTTP 语义约定；
   - `db_query` → `SPAN_KIND_CLIENT`，套 Database 语义约定。
3. **其余事件不发 span**：`log` / `ui_interaction` / `screen_view` 不是"调用跨度"，`crash` / `hang` 留在 logs 信号（附 `exception.*` 属性）。
4. **id 优先透传、span 缺失才派生**（见 §6）：`trace_id` 与 `span_id` 合法即透传（均为固定长度 hex）；仅 span 缺失 `span_id` 时确定性派生，保证同一事件重复导出得到同一 `spanId`，重试与重放幂等。
5. **OTLP 是传输格式，不是存储格式**：`payload` 展平后作为属性发送，不做二次脱敏——脱敏已在 logger 层完成（C6）。

## 3. 事件 → LogRecord

| Schema v1 | OTLP LogRecord | 说明 |
| --- | --- | --- |
| `ts` | `timeUnixNano` + `observedTimeUnixNano` | RFC3339 → epoch 纳秒（字符串形式，见 §5） |
| `message` | `body.stringValue` | 已脱敏，直接作为 body |
| `level` | `severityText` + `severityNumber` | 见 §4 |
| `service` | resource `service.name` | |
| `env` | resource `deployment.environment` | OTel 语义约定 |
| `session_id` | resource `session.id` | OTel 语义约定 |
| `trace_id` | `traceId` | 见 §6；无 `trace_id` 时省略该键 |
| `event_type` | attribute `agent.event.type` | Agent 主过滤键 |
| `agent_auto` | attribute `agent.auto`（bool） | 区分机器时间线 / 业务手写 |
| `subsystem` | attribute `agent.subsystem` | 自定义键加 `agent.` 前缀 |
| `category` | attribute `agent.category` | 同上 |
| `user_id` | attribute `enduser.id` | 语义约定中的间接标识 |
| `payload.<k>` | attribute `payload.<k>` | 逐键展平，类型见 §5 |
| `span_id` | `spanId` | 统一追踪模型的操作跨度标识；合法（16 位小写 hex）时原样透传，缺失才派生（§6）；无 `trace_id` 时不写入 |
| （派生） | `spanId` | 仅当该事件同时产出 span 且未自带 `span_id` 时派生（§7） |

补充：`crash` / `hang` 额外从 `payload` 提取

| payload | attribute |
| --- | --- |
| `exception` / `exception_type` | `exception.type` |
| `exception_message` / `message` | `exception.message` |
| `stack` / `stacktrace` | `exception.stacktrace` |

## 4. 级别映射（6 → 6）

| agent-log | `severityText` | `severityNumber` |
| --- | --- | --- |
| `trace` | `TRACE` | 1 |
| `debug` | `DEBUG` | 5 |
| `info` | `INFO` | 9 |
| `warn` | `WARN` | 13 |
| `error` | `ERROR` | 17 |
| `critical` | `FATAL` | 21 |

- OTel 的 severity number 以 4 为步长留出细分空间，我们只使用规范值。
- 未知 level **降级为 INFO**，绝不让一次导出因为脏数据整体失败。

## 5. 值类型（protobuf JSON 映射）

| Python 值 | AnyValue | 备注 |
| --- | --- | --- |
| `bool` | `boolValue` | 先于 `int` 判断（`bool` 是 `int` 子类） |
| `int` | `intValue`（**字符串**） | JSON 数字是 double，64 位整数必须字符串化 |
| `float` | `doubleValue` | |
| `str` | `stringValue` | |
| `list` / `tuple` | `arrayValue.values` | 元素递归 |
| `dict` | `kvlistValue.values` | 只展平一层，嵌套保持结构（避免键爆炸） |
| `None` | （跳过） | 不产出该属性 |
| 其他对象 | `stringValue`（`str(v)`） | 兜底，宁可丢类型也不丢事件 |

`timeUnixNano` / `startTimeUnixNano` / `endTimeUnixNano` 同样按 int64 规则以**字符串**发送。

## 6. id 规则（确定性）

统一追踪模型中，`trace_id` 为 **32 位小写 hex**（8 字节，与 OTLP `traceId` / W3C `traceparent` 的 trace-id 同构），`span_id` 为 16 位小写 hex（8 字节）。两者策略一致：**合法值透传（大写归一为小写），非法值在写入边界丢弃（事件照写）—— 适配器绝不变形、绝不派生用户 id**：

| 场景 | 规则 |
| --- | --- |
| 事件自带合法 `trace_id` | 原样透传（大写归一为小写）——日志、OTLP、Jaeger 三处同一个值 |
| `trace_id` 非法或缺失 | 写入边界丢弃该字段，事件本身照写；LogRecord 不带 `traceId`/`spanId` |
| 事件自带合法 `span_id` | 原样透传；LogRecord 与 span 共用该 id |
| `span_id` 缺失或非法（仅当该事件要发 span） | `sha256("agentlog:span:" + session_id + trace_id + event_type + ts + message)[:16]` 确定性派生 |
| 无 trace 的事件要发 span | 用 `sha256("agentlog:session:" + session_id)[:32]` 作为该会话的合成 trace |

要点：

- **为什么不哈希非 hex 的 `trace_id`**：哈希不可逆——调用方写 `checkout-flow-42`，Jaeger 里只能看到 `7f3a…`，反推不回原值，需要额外的补偿属性才能搜索；且「同一个 id 的两种写法」可能派生出两个不同 trace（如 UUID 带横线与去横线）。强制 hex 让割裂在源头消失：**想用 trace 关联，就按规范填；不填或不规范，丢的是 trace 关联，不是日志**。
- **上游非 hex id 的对接**：在系统边界（网关 / 入口服务）显式转换为 32 位 hex 并自行维护映射——这是业务决策，不由日志库偷偷变形（哈希提供的「聚合」无法与上游真实链路对上，是假关联）。
- **生成便利**：各端 SDK 提供 `newTraceId()`（uuid4 去横线）；session id 默认值同为 32 位 hex，因此 `trace_id = session_id` 这个最自然的绑定永远合法。
- **span 派生不引入随机性**：重放/重试不会产生重复 span；`span_id` 缺失时的派生种子包含原始 `trace_id` 字符串，六端一致。
- **同一会话无 trace 的多个 span 归入同一条合成 trace**，而不是每个 span 一条 trace（后者在 Jaeger 里会变成大量孤立单 span 链路）。
- `traceId`/`spanId` 在 OTLP/JSON 中是 **hex 字符串**（OTLP 对这两个字段的 JSON 表示是 hex，而非 protobuf 通用的 base64）——这是规范特例，务必不要按 base64 处理。

## 7. 操作 span

### 7.1 `network_request`（HTTP 语义约定）

- `name`：`"<METHOD> <url>"`
- `kind`：`SPAN_KIND_CLIENT`（3）
- 时间窗：`startTimeUnixNano = ts`，`endTimeUnixNano = start + duration_ms × 1e6`（缺 `duration_ms` 时为 0 长度 span）
- 属性：

| payload | attribute |
| --- | --- |
| `method` / `http_method` | `http.request.method` |
| `url` / `url_full` | `url.full` |
| `url` 的 host 部分 | `server.address` |
| `status_code` / `status` | `http.response.status_code`（int） |
| 状态码 ≥ 400 或 `error` 非空 | `error.type`（状态码字符串或错误文本） |

- `status`：仅失败时写 `{"code": 2 /* ERROR */, "message": <name>}`；成功保持 UNSET（不写 OK，避免噪音）。

### 7.2 `db_query`（Database 语义约定）

- `name`：`"<operation> <statement>"`
- `kind`：`SPAN_KIND_CLIENT`（3）
- 时间窗同 7.1（`duration_ms`）
- 属性：`db.system`（`db_system`/`system`）、`db.operation`（`operation`/`op`）、`db.statement`（**规范键 `statement`**）、失败时 `error.type`。

> **payload 词表**：`db_query` 的 SQL 文本在六端一律写入 **`statement`**，禁止写 `query` / `sql`。详见 `README.md` §3.5「payload 标准词表」。

## 8. Resource 与批次组织

- 每个批次按 `(service, env, session_id)` 分组，一组一个 `resourceLogs` / `resourceSpans`。
- 组内 `scope` = `{"name": "agentlog.otlp", "version": <sdk version>}`。
- resource 固定包含：`service.name`、`deployment.environment`（若有）、`session.id`（若有）、`telemetry.sdk.name="agent-log"`、`telemetry.sdk.language=<lang>`、`telemetry.sdk.version`。
- 调用方可追加 `extra_resource`（如 `service.version`），冲突时 agent-log 自身字段优先。

## 9. 传输

### 9.1 请求形状

- 每个 OTLP 请求只承载**一种信号**：logs → `POST <collector>/v1/logs`，traces → `POST <collector>/v1/traces`。
- `Content-Type: application/json`（本规范使用 OTLP/JSON 而非 protobuf，便于零依赖实现）。
- body 为空（无任何 resource 组，例如只有普通日志、没有操作事件时的 traces）**不发请求**，避免无意义往返。
- 默认 endpoint `http://localhost:4318`（OTel Collector 的 OTLP/HTTP 端口）；endpoint 末尾多余 `/` 会被归一化。

### 9.2 内置 exporter 与重试策略

适配器只产出 body；把它送上网络的是各端的 **exporter**（Go `agentlog/otlp_http.go`、Python `agentlog/otlp_http.py`）。exporter 刻意做得很小：**不是队列**，不做定时批量、不做磁盘缓冲、不做背压——生产环境应指向本地 Collector，由 Collector 负责持久化。

| 响应 | 处理 |
| --- | --- |
| `2xx` | 成功 |
| `408` / `429` / `5xx` | 可重试，指数退避（默认 base 100ms，逐次翻倍，上限 64×） |
| 其他 `4xx` | **永久失败**：payload 结构错误或未授权，重试只会放大错误，立即抛出 |
| 传输层错误（连接拒绝、超时） | 可重试 |

其他约定：

- 默认重试次数 2（共 3 次尝试），默认超时 10s；调用方可调。
- **顺序**：先 logs 后 traces；遇到永久失败立即中止该批次并抛错，绝不静默丢数据（调用方需要知道丢了）。
- 导出为**幂等**：同一事件重复导出得到相同 `traceId`/`spanId`（§6），重试不会产生重复链路节点。
- 脱敏在 logger 层已完成（C6），exporter 不再二次处理隐私数据。

### 9.3 端到端验证

- `tools/otlp-compat-verify/collector.py`：零依赖假 Collector（`http.server`），校验每个 LogRecord/Span 的结构不变量（id 长度与大小写、`timeUnixNano` 为字符串、severityNumber 为整数、span 时间窗不倒挂、resource 含 `service.name`）。可独立起服务（`--expect-records/--expect-spans` 用作 CI 门禁），也可被脚本导入。
- `tools/otlp-compat-verify/e2e_demo.py`：起 Collector → 真跑 Go 与 Python 示例（`AGENTLOG_OTLP_ENDPOINT` 触发导出）→ 断言收到的记录数、事件类型、span 语义，以及**跨语言同一绑定 span 产出同一组 OTLP id**。

## 10. 实现状态

| 端 | 状态 | 入口 |
| --- | --- | --- |
| Python | ✅ 适配器 + ✅ exporter（v1.2.0；统一追踪模型边界校验、`new_trace_id()`） | `agentlog/otlp.py`：`to_otlp` / `to_otlp_logs` / `to_otlp_spans` / `event_to_log_record` / `event_to_span` / `OTLPSink`；`agentlog/otlp_http.py`：`OTLPExporter` |
| Go | ✅ 适配器 + ✅ exporter（v1.2.0；`NormalizeTraceID` / `NewTraceID`） | `agentlog/otlp.go`：`ToOTLP` / `ToOTLPLogs` / `ToOTLPSpans` / `EventToLogRecord` / `EventToSpan` / `OTLPSink`；`agentlog/otlp_http.go`：`OTLPExporter` |
| Java | ✅ 适配器（v1.2.0；零第三方依赖，仅 `java.base`；`CoreTypes.TraceId`） | `OtlpMapper`：`toOtlp` / `toOtlpLogs` / `toOtlpSpans` / `eventToLogRecord` / `eventToSpan` / 内嵌 `OtlpSink implements LogSink` |
| Web / TS | ✅ 适配器（v1.2.0；浏览器可用：同步 SHA-256 自实现、纳秒走 BigInt；`normalizeTraceId` / `newTraceId`） | `src/otlp.ts`：`toOtlp` / `toOtlpLogs` / `toOtlpSpans` / `eventToLogRecord` / `eventToSpan` / `createOtlpSink`；`src/ids.ts`、`src/trace.ts` |
| Kotlin / Android | ✅ 适配器（v1.2.0；复用包内 `Json` 树，零第三方依赖；`TraceId` object） | `OtlpMapper`（`object`）：`toOtlp` / `toOtlpLogs` / `toOtlpSpans` / `eventToLogRecord` / `eventToSpan` / 内嵌 `OtlpSink : LogSink` |
| Swift / macOS | ✅ 适配器（v1.2.0；只依赖 Foundation + CryptoKit；`TraceIdentifier`） | `OtlpMapper`：`toOtlp` / `toOtlpLogs` / `toOtlpSpans` / `logRecord(for:)` / `span(for:)` / `json(_:)`；`AgentLogExporter.otlpBatch(extraResource:)` |

> 表内状态只针对 **OTLP 适配器/exporter**。统一追踪模型的**边界校验**六端已全部落地：各有 `normalize` + 序列化边界丢弃非法值的实现，session id 默认值均为 32-hex，各端提供 `newTraceId()` 类便利函数。
>
> **HTTP exporter 目前仅 Python / Go 两端有**；其余四端只有适配器（结构转换是纯函数，
> 传输交回宿主平台：Java 用 `HttpClient`、Kotlin 用 `OkHttp`、Web 用 `fetch`、Swift 用 `URLSession`，
> 由接入方按自身重试/退出策略组装，避免把平台 HTTP 栈硬塞进底座）。

### 10.1 跨端一致性验证

`tools/otlp-compat-verify/xlang_verify.py` 用**同一批 6 条样例事件**（`xlang/samples.json`，
覆盖 log / network_request / db_query / crash / ui_interaction 五类，外加一条**非 hex
`trace_id`** 样例验证六端都按无 trace 处理）逐端 dump 出
`logs` + `traces` 两份 OTLP/JSON，与 Python 基准做结构化比对：

```bash
python3 tools/otlp-compat-verify/xlang_verify.py            # 六端全跑
python3 tools/otlp-compat-verify/xlang_verify.py --only java,go
```

- 比对前归一化：键递归排序、`KeyValue` 列表按 `key` 排序（语义无序）、剔除逐语言必然不同的
  `telemetry.sdk.language`。
- 各端 dump harness 在 `xlang/harness/`：`dump.py` / `main.go` / `XlangMain.java` / `Dump.kt` /
  `dump.mjs` / `main.swift`，都只做「读样例 → 调本端 `toOtlp` → 写文件」，不含任何断言或期望值。
- 工具链缺失或构建失败会 `SKIP` 而非判失败；一旦某端可用就必然参与比对（不存在"悄悄跳过"）。
- 退出码：全一致 `0`、存在真实差异 `1`、基准不可用或全部跳过 `2`。

实测（六端全部可用）：`java` / `kotlin` 与基准**逐字一致**，`go` / `web` / `swift` 仅剩下述
数字表示差异，`traces` 六端**逐字一致**。

### 10.2 已知跨语言差异（仅数字表示，语义等价）

比对发现的差异全部可归因于**语言数字模型**，而非映射逻辑，因此被工具归类为
`number-model` 并容忍；其余任何差异都判失败。

| 差异 | 场景 | 原因 |
| --- | --- | --- |
| `intValue:"120"` ↔ `doubleValue:120.0` | `payload.duration_ms: 120.0` | JS/Swift/Python 不区分 int/float 或按解析路径落成整数值；Kotlin/Java 的解析器保留 `Double` |
| `doubleValue:200` ↔ `intValue:"200"` | `payload.status_code: 200` | Go 用 `encoding/json` 解码输入时数字统一成 `float64`，无法回推原始整数性 |

两者在 OTLP 语义上等价（`intValue` 与 `doubleValue` 都是 `AnyValue` 的数值分支）。若要完全消除：

- Go 侧需改用 `json.Decoder.UseNumber()` 并按字面量判断整数性（会改变对外 `map[string]interface{}` 的值类型，属于破坏性变更，暂不做）；
- 其余端需在解析层引入"整数/浮点"标记（等于自造数字类型，收益低）。

**注意**：这一差异只影响 `payload` 里的原始数字。适配器自身产出的整数字段
（`severityNumber`、`kind`、`http.response.status_code` 的 `intValue`、纳秒字符串）六端一致，
已验证逐字相同。

验证方式：

- 端内单测：Python `tests/test_otlp.py`（38 项）+ `tests/test_otlp_http.py`（14 项）；Go `agentlog/otlp_test.go`（25 项）+ `agentlog/otlp_http_test.go`（11 项）+ `agentlog/span_test.go`（6 项）；Java `OtlpMapperTests`（27 项）；Web `src/otlp.test.ts`（37 项）；Kotlin `OtlpMapperTests`（25 项）；Swift `Tests/AgentLogTests/OtlpMapperTests.swift`（25 项）。六端断言的是**同一组不变量**（级别表、id 派生、LogRecord 形状、HTTP/DB span 语义、resource 分组、extraResource 冲突）。
- 规范对照脚本：`tools/otlp-compat-verify/validate.py`（零依赖，套用真实 `schema/log-event.schema.json` 校验 5 类样例事件）。
- 端到端：`tools/otlp-compat-verify/e2e_demo.py`（真实 HTTP 往返，Go + Python 双端到同一 Collector）。
- 跨端一致性：`tools/otlp-compat-verify/xlang_verify.py`（六端全量，见 §10.1）。

## 11. 风险与注意

1. **semconv 版本漂移**：部分属性（如 `db.*`、`http.request.method`）在 OTel 规范中仍标 Experimental。各端实现必须把 semconv 键收敛在一处常量，便于随版本升级。
2. **`payload` 无白名单**：OTLP 属性数量无硬上限但后端有（如 Datadog 对属性数/长度有限制）。大 payload 建议在 Collector 侧做 `attributes/delete` 或采样。
3. **高基数字段**：`payload.url` 含动态 id 时会把 `url.full` 变成高基数；如需聚合，应在 Collector 侧改为 `http.route` 模板。
4. **`trace_id` 不派生**：非法/缺失 `trace_id` 在写入边界直接丢弃（事件照写），绝不做哈希变形。跨系统串联的上游非 hex id 映射是业务决策，应在系统边界（网关 / 入口服务）显式完成，不由日志库偷偷处理（假关联无法与上游真实链路对上）。
