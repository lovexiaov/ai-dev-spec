# 贡献规范（CONTRIBUTING）

本仓库是「AI 驱动开发」脚手架模板。无论人还是 AI Agent 提交，都请遵守以下约定。

## 分支

- 默认分支为 `main`。
- 新特性：从 `main` 切 `feat/<name>`；修复：切 `fix/<name>`；纯规范/文档：`chore/<name>` 或 `docs/<name>`。
- 合并前须经 PR；远端 CI（`.github/workflows/ci.yml`）通过且人工 review 后方可合入主分支。

## 提交信息（Conventional Commits）

- 格式：`<type>(<scope>): <subject>`，例如 `feat(observability): add traceId propagation`。
- 允许的 `type`：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `build` / `ci` / `chore` / `revert`。
- 执行 `pnpm install` 会激活 husky + commitlint，**提交信息不合规会被本地拦截**；CI 会再校验一次。
- Agent 的「节点检查点」提交统一用 `chore: state checkpoint`（见 `AGENTS.md` 的 Clock-out 约定）。

## 密钥与敏感信息（红线，不可违反）

- 密钥、token、`.env` 永不进仓（详见 `AGENTS.md` 的 NEVER 规则）。
- pre-commit 钩子会拦截 `.env` 与常见密钥模式；CI 也会做密钥扫描。

## 可观测子模块（两个独立仓库）

| 子模块路径                            | 仓库                                                                    | 内容                                                                                          |
| ------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `logging-framework/web/Observability` | `agent-log-web`（`https://github.com/lovexiaov/agent-log-web.git`）     | Web 可观测包 `@scaffold/observability`：结构化日志（Schema v1）、trace、metrics、前端崩溃捕获 |
| `logging-framework/macos/AgentLog`    | `agent-log-macos`（`https://github.com/lovexiaov/agent-log-macos.git`） | macOS 日志框架：swift-log + Pulse + KSCrash，自动埋点                                         |

- 首次拉取：`git submodule update --init`（或 clone 时加 `--recurse-submodules`）。
- 追新：`git submodule update --remote <path>`，随后提交指针变更。
- Web 子模块注册在 `pnpm-workspace.yaml`，根 `pnpm -r typecheck|test` 会连带跑它的门禁；它自带 tsconfig/eslint，**不要在根配置里改它的规则**。
- 业务项目请改用**包管理器 / SPM 引用**这些仓库，不要 fork 进本仓库。

## 规范优先于代码

- 改动架构或新增约束前，先更新 `docs/constitution.md` 与对应 spec（`docs/specs/`），再让 Agent 实现。
- 新特性流程：`spec → plan（人批）→ tasks → 实现 → 验收测试 → PR`。
