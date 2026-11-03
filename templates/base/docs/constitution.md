# Constitution（项目宪法）

> 本文件记录「这个项目信奉什么」，由**人类 owner** 维护，不可被 Agent 随意修改。
> 它比 `.agent/AGENTS.md` 更上层：AGENTS.md 讲「怎么跟 Agent 协作」，这里讲「我们绝不妥协的原则」。
> **本宪法语言无关**——不绑定任何实现语言；技术栈基线以各模块自身约定为准。

## 1. 开发范式

- 采用 **Spec-Driven Development**：规范先于代码，人决策、Agent 实现。
- 任何业务代码改动，必须追溯到 `docs/specs/<feature>/` 下的规范，且 `plan.md` 已获人工批准。

## 2. 不可违反的硬约束

1. **可观测性一等公民**：所有外部调用、错误、AI 交互必须带 `traceId` 并结构化上报；崩溃必须上报。
2. **密钥永不进仓**：任何凭据只允许通过环境变量/密钥管理，禁止提交到 git。
3. **小步快跑**：PR 一次只解决一个关切点；禁止巨型 PR。
4. **测试即验收**：`spec.md` 的验收条件必须有对应自动化测试，跑不过即未完成。
5. **不可逆操作需人工确认**：删除数据、改写历史、发布、外发消息必须经人确认。
6. **状态外置、进度可交接**：任务进度、决策、验证证据必须写入仓库（`docs/specs/<feature>/handoff.md` / Git 提交），而非对话历史。

## 3. 中立契约（不随语言变）

- 门禁契约：`docs/gate-contract.md`——每个模块经 `.toolchain.json` 声明适配器，暴露 lint/typecheck/test/build。
- 日志接口：`docs/logging-framework/INTERFACE.md`——所有 logger 必须 conform。
- 线格式：`docs/logging-framework/schema/log-event.schema.json`——snake_case、6 档 level、字段集封闭。
- 配置：`config/logging.config.json`（Schema：`config/logging.config.schema.json`）——各语言读同一份。
- 追踪：OpenTelemetry / W3C `traceparent`。

## 4. 术语表（避免词汇漂移导致的「编译通过但语义错」）

- `workspace` = 代码与数据库中的 `organization`
- `seat` = 计费用户，而非任意用户

## 5. 决策记录

重大架构/约束变更写入 `docs/decisions/`（ADR 风格），说明「背景—决策—后果」。
