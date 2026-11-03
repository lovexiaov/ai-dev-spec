# AGENTS.md — 全局治理（给 AI 编码 Agent 看）

> 本文件是「伤疤」——只在 Agent 犯过错、被纠正后，才把教训沉淀成一条规则。保持精简。
> 人类贡献者请看 README.md；本文件是写给 AI 的「入职手册」。

## 1. 项目概述

- 采用 **AI 主导开发（Spec-Driven Development）**：人负责需求与决策，Agent 负责实现。
- **架构是语言中立的（language-agnostic）**：根仓库只持有「中立契约」——`docs/constitution.md`、
  `docs/spec-format.md`、`docs/gate-contract.md`、`docs/logging-framework/INTERFACE.md` 与
  `schema/log-event.schema.json`；具体语言工具由 `tooling/adapters/*` 适配。
- 任何语言（TypeScript / Swift / Python / Go …）实现的模块，都通过根目录的 `.toolchain.json`
  声明自己用哪个适配器，并暴露 `lint / typecheck / test / build` 四个标准阶段。

## 2. 必跑命令

- **每次提交前必须跑通门禁**：`node tooling/gate-runner.mjs`（等价于 CI 远端门禁）。
- 具体阶段命令由适配器翻译，不要直接写死 `eslint` / `swift` / `pytest`。

## 3. 三层边界（Three-tier Boundaries）

### ✅ ALWAYS

- 改动任何代码前，先读对应特性的 `docs/specs/<feature>/spec.md` 与 `plan.md`。
- 所有外部调用、日志、错误都必须携带 `traceId`，并结构化上报。
- 新增/修改代码必须补或更新测试，使 `spec.md` 的验收清单可被自动验证。
- 优先复用已有依赖与代码模式。

### ⚠️ ASK FIRST

- 删除或修改非当前任务的文件（跨包/跨目录）。
- 引入新的第三方依赖。
- 变更 API 契约、或 `docs/constitution.md` 中的硬性约束。
- 任何「不可逆或对外可见」的操作（删除数据、改写历史、发布、外发消息）。

### 🚫 NEVER

- 提交密钥、token、`.env` 文件或任何凭据到仓库。
- 在 `plan.md` 未含「✅ Human Approval」标记前，修改业务代码。
- 为图省事引入 wildcard import 或绕过类型检查。

## 4. 人工闸门

- **规划闸门**：进入实现前，必须在 `docs/specs/<feature>/plan.md` 的 `## ✅ Human Approval` 获人工勾选。
- **合并闸门**：CI 任一阶段失败即阻断；验收以 `spec.md` 的 Acceptance Criteria 为准（**可测**才算完成）。

## 5. 质量基线

- 提交遵循 Conventional Commits：`feat:` / `fix:` / `refactor:` / `test:` / `docs:`。
- 日志遵循 `docs/logging-framework/INTERFACE.md` 统一接口；禁止用 `console.log` / `print` 作为生产日志手段。
- 前端/客户端错误务必经统一 logger 上报，绝不吞掉异常。

## 6. 强制约束层（机器守门）

1. **Git Hooks**：`pre-commit` 拦截密钥 + 跑 lint；`pre-push` 跑通 typecheck+test。
2. **CI（远端）**：经中立 `tooling/gate-runner.mjs` 跑 lint/typecheck/test/build + 安全扫描，任一失败即阻断。

- 紧急绕过（需人工知晓并事后补规则）：`SKIP_PLAN_CHECK=1` / `SKIP_BASH_GUARD=1`；绕过会被记入日志，不可滥用。
- 详见 `docs/gate-contract.md`。
