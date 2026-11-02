# Constitution（项目宪法）

> 本文件记录「这个项目信奉什么」，由**人类 owner** 维护，不可被 Agent 随意修改。
> 它比 `AGENTS.md` 更上层：AGENTS.md 讲「怎么跟 Agent 协作」，这里讲「我们绝不妥协的原则」。

## 1. 开发范式

- 采用 **Spec-Driven Development**：规范先于代码，人决策、Agent 实现。
- 任何 `src/` 的改动，必须追溯到 `docs/specs/<feature>/` 下的规范，且 `plan.md` 已获人工批准。

## 2. 不可违反的硬约束

1. **可观测性一等公民**：所有外部调用、错误、AI 交互必须带 `traceId` 并结构化上报；前端崩溃必须上报。
2. **密钥永不进仓**：任何凭据只允许通过环境变量/密钥管理，禁止提交到 git。
3. **小步快跑**：PR 一次只解决一个关切点；禁止巨型 PR。
4. **测试即验收**：`spec.md` 的验收条件必须有对应自动化测试，跑不过即未完成。
5. **不可逆操作需人工确认**：删除数据、改写历史、发布、外发消息必须经人确认。
6. **状态外置、进度可交接**：任务进度、决策、验证证据必须写入仓库（`docs/specs/<feature>/handoff.md` / `tasks.md` / Git 提交），而非对话历史；任何新 Agent 读文件即可恢复上下文继续干活。

## 3. 技术栈基线（锁定的事实，变更需走决策记录）

- 语言/运行时：TypeScript + Node.js（LTS）
- 前端：React + Vite
- 包管理：pnpm（禁止混用 npm/yarn）
- 可观测：`@scaffold/observability`（独立仓库 `agent-log-web`，submodule `logging-framework/web/Observability`），Sentry 接 source map
- 追踪：OpenTelemetry / W3C `traceparent`

## 4. 术语表（避免词汇漂移导致的「编译通过但语义错」）

- `workspace` = 代码与数据库中的 `organization`
- `seat` = 计费用户，而非任意用户

## 5. 决策记录

重大架构/约束变更写入 `docs/decisions/`（ADR 风格），说明「背景—决策—后果」。
