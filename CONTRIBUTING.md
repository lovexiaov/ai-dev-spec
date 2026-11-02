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

## agent-log-macos 子模块

- `logging-framework/macos/AgentLog` 是 git submodule，指向 `agent-log-macos` 仓库（`https://github.com/lovexiaov/agent-log-macos.git`）。
- 首次拉取：`git submodule update --init`。
- 追新：`git submodule update --remote logging-framework/macos/AgentLog`，随后提交指针变更。
- 业务项目请改用**纯 SPM 引用**该仓库，不要把它 fork 进本仓库。

## 规范优先于代码

- 改动架构或新增约束前，先更新 `docs/constitution.md` 与对应 spec（`docs/specs/`），再让 Agent 实现。
- 新特性流程：`spec → plan（人批）→ tasks → 实现 → 验收测试 → PR`。
