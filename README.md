# ai-dev-spec · AI 开发脚手架

一套面向「**人退居需求与决策者、AI Agent 主导编码**」新范式的项目初始化脚手架。
它把四条关键注意点**固化进目录、配置与核心模块**，让新项目从第一行代码起就自带约束、可观测、验收与进度可交接机制。

## 四条原则（本脚手架为何这样设计）

1. **人 = 需求提供者 + 关键决策者**：规范先于代码。先写 `spec → plan（人批）→ tasks`，再让 Agent 实现。
2. **日志 / 可观测（尤其前端）是硬通货**：可观测核心包是独立仓库（Web `agent-log-web`、macOS `agent-log-macos`），以 submodule 挂在 `logging-framework/`，结构化日志、traceId 串联、前端崩溃捕获、AI 交互事件开箱即用。
3. **约束 AI + 明确验收**：`AGENTS.md` 三层边界做软约束，`Git Hooks + Agent Hooks + CI` 三层硬门禁做强制，`spec.md` 验收条件即测试。
4. **进度可观测 / 可跟踪 / 可随时换人**：状态外置到仓库（`handoff.md` / `tasks.md` / Git 提交 + 进度日志），任何新 Agent 读文件即续作，无需重述上下文。

## 快速开始

**前置**：Node ≥ 20、Git。pnpm 版本由 `package.json` 的 `packageManager` 锁定为 `12.14.0`，用 corepack 自动切换。

```bash
# 1. 克隆时必须带子模块：两个可观测包是独立仓库，以 submodule 挂在 logging-framework/ 下。
#    Web 那个同时注册为 pnpm workspace 成员，缺失会导致 pnpm install 直接失败。
git clone --recurse-submodules https://github.com/lovexiaov/ai-dev-spec.git
cd ai-dev-spec

# 2. 让 corepack 按 packageManager 装上正确的 pnpm（避免与本机版本冲突）
corepack enable

# 3. 装依赖，会自动激活 husky 并装好三道 Git Hooks（失败可手动补救：pnpm exec husky）
pnpm install

# 4. 跑与 CI 一致的三道门禁，全绿才算环境可用
pnpm lint && pnpm typecheck && pnpm test
```

> **忘了带子模块？** 子模块目录会是空的，`pnpm install` 报
> `the lockfile records importers["logging-framework/web/Observability"], but that project's directory has no package.json`。
> 补救：`git submodule update --init --recursive` 后重新 `pnpm install`。

> `pnpm dev` 等价于 `pnpm -r --parallel --if-present dev`：本模板尚未内置业务代码，
> 等你在工作区里加了带 `dev` 脚本的包，它会自动并行拉起这些开发服务。

> 使用 Claude Code 时，`.claude/settings.json` 里的 Agent Hooks 会在你改动文件/执行命令时自动生效；
> Cursor / WorkBuddy 等工具则靠 Git Hooks（提交/推送时）兜底强制。

## 强制约束（Hooks 已就位）

为了让 AI「乖乖听话」，约束不只是写在 `AGENTS.md` 里的建议，而是三层机器强制：

| 层级            | 触发时机                                | 强制内容                                                                                                  | 文件                                          |
| --------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| **Git Hooks**   | `git commit` / `push`（对任何工具生效） | 拦密钥/.env、跑 ESLint（禁 `console.log`）、强制 Conventional Commits、push 前跑通 typecheck+test         | `.husky/pre-commit` `commit-msg` `pre-push`   |
| **Agent Hooks** | Agent 改文件 / 跑命令时（Claude Code）  | 无批准 plan 禁改 `src/`；拦截高危命令；改完即 lint 自纠                                                   | `.claude/settings.json` `scripts/hooks/*.mjs` |
| **CI**          | PR / push 到 main                       | `quality`(lint/typecheck/test/构建) + `security`(gitleaks 密钥扫描 + `pnpm audit --prod`)，任一失败即阻断 | `.github/workflows/ci.yml`                    |

紧急绕过（需人工知晓，会记入日志）：`SKIP_PLAN_CHECK=1` / `SKIP_BASH_GUARD=1`。

## 关键文件导航

| 你想做什么                        | 看哪里                                                                                                      |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 了解全局协作规则 / 约束 Agent     | [`AGENTS.md`](./AGENTS.md)                                                                                  |
| 了解项目不可妥协的原则            | [`docs/constitution.md`](./docs/constitution.md)                                                            |
| 开始一个新特性（规范三件套）      | 复制 [`docs/specs/_template/`](./docs/specs/_template)                                                      |
| 交接 / 续接 Agent 进度            | 看 [`docs/specs/_template/handoff.md`](./docs/specs/_template/handoff.md) + `AGENTS.md` §7                  |
| 配置日志级别 / 脱敏 / Sentry      | [`config/logging.config.ts`](./config/logging.config.ts)                                                    |
| 接入可观测核心包（Web）           | [`logging-framework/web/Observability`](./logging-framework/web/Observability)（submodule `agent-log-web`） |
| 通用日志规范（Schema v1）         | [`docs/logging-framework/`](./docs/logging-framework)                                                       |
| 查看 CI 硬性闸门                  | [`.github/workflows/ci.yml`](./.github/workflows/ci.yml)                                                    |
| 查看强制约束层（Git/Agent Hooks） | [`DESIGN.md §7`](./DESIGN.md) · [`.husky/`](./.husky) · [`.claude/settings.json`](./.claude/settings.json)  |
| 改 `src/` 被拦？看计划批准逻辑    | [`scripts/hooks/check-plan.mjs`](./scripts/hooks/check-plan.mjs)                                            |
| 完整设计方案与来源                | [`DESIGN.md`](./DESIGN.md)                                                                                  |

## 推荐工作流（Spec-Driven）

1. 在 `docs/specs/<feature>/spec.md` 写明目标、非目标、**可测验收条件**。
2. Agent 起草 `plan.md`，人在 `## ✅ Human Approval` 区块批准后，才改 `src/`。
3. 把工作拆进 `tasks.md`，每条带「改哪些文件 + 跑哪些命令 + 完成判定」。
4. Agent 实现并跑通 `pnpm lint && pnpm typecheck && pnpm test`；reviewer 子 Agent 二审。
5. 收工前按 `AGENTS.md` §7 更新 `handoff.md` 并提交 `chore: state checkpoint`（换人无缝续接）。
6. PR 触发 CI 硬闸门；人工 review 后合并。

> 维护哲学：`AGENTS.md` 当「伤疤」写——每次 Agent 犯错被纠正，沉淀为一条规则；超过 200 行就下沉到 `docs/` 或 `.agents/`。
