# AGENTS.md — 全局治理（给 AI 编码 Agent 看）

> 原则：本文件是「伤疤」——只在 Agent 犯过错、被纠正后，才把教训沉淀成一条规则。
> 保持精简（≤200 行）。任何一行若从未改变过 Agent 行为，就删掉它。
> 人类贡献者请看 README.md；本文件是写给 AI 的「入职手册」。

## 1. 项目概述

- 这是一个采用 **AI 主导开发（Spec-Driven Development）** 的项目：人负责需求与决策，Agent 负责实现。
- **架构是语言中立的（language-agnostic）**：根仓库只持有「中立契约」——`docs/constitution.md`、`docs/spec-format.md`、`docs/gate-contract.md`、`docs/logging-framework/INTERFACE.md` 与 `schema/log-event.schema.json`；具体语言工具由 `tooling/adapters/*` 适配。脚手架自身用 TypeScript 实现（gate-runner 是 Node 脚本），但它强制的**契约与产出物无关任何语言**（详见 `DESIGN.md` 顶部「语言中立架构」）。
- 当前根仓库的「实现语言」是 TypeScript + Node.js（pnpm）；Web 端日志实现在 `logging-framework/web/Observability`（`agent-log-web`，npm `@scaffold/observability`），macOS 端在 `logging-framework/macos/AgentLog`（`agent-log-macos`），二者都是中立 `docs/logging-framework/INTERFACE.md` 的实现。
- 业务代码在 `src/`，特性规范在 `docs/specs/<feature>/`。

## 2. 必跑命令（Agent 自己发现不了的）

- 安装依赖：`pnpm install`（克隆时必须 `--recurse-submodules`，否则 Web 子模块缺失导致 install 失败）
- 启动开发：`pnpm dev`（模板尚无业务代码时为空操作；加入带 `dev` 脚本的包后自动并行拉起）
- 快速测试：`pnpm test`（已内置 `--bail`：任一 workspace 包测试失败即终止）
- 类型检查：`pnpm typecheck`
- Lint & 格式：`pnpm lint`
- **每次提交前必须跑通 `pnpm lint && pnpm typecheck && pnpm test`**。
- **用本脚手架生成新项目**：`node tooling/init.mjs <lang> <dir>`（`lang` = typescript/swift/python）。
- **为已有项目追加约束+日志**：`node tooling/add-to-existing.mjs <lang> <dir>`（不碰业务代码）。
- 门禁编排器 `tooling/gate-runner.mjs` 是语言中立的，新增语言只需加 `tooling/adapters/<lang>.mjs`。

## 3. 三层边界（Three-tier Boundaries）

### ✅ ALWAYS（总是要做）

- 改动任何代码前，先读对应特性的 `docs/specs/<feature>/spec.md` 与 `plan.md`。
- 所有外部调用、日志、错误都必须携带 `traceId`（见 `logging-framework/web/Observability`）。
- 新增/修改代码必须补或更新测试，使 `spec.md` 的验收清单可被自动验证。
- 优先复用已有依赖与代码模式，不重复造轮子。

### ⚠️ ASK FIRST（先问再做）

- 删除或修改非当前任务的文件（跨包/跨目录）。
- 引入新的第三方依赖（需在 PR 描述里说明原因）。
- 变更数据库 schema、API 契约、或 `docs/constitution.md` 中的硬性约束。
- 任何「不可逆或对外可见」的操作（删除数据、改写历史、发布、外发消息）。

### 🚫 NEVER（绝对禁止）

- 提交密钥、token、`.env` 文件或任何凭据到仓库。
- 改动 `legacy/`、`infra/`、`.github/workflows/` 而未获人工 review。
- 在 `plan.md` 未含「✅ Human Approval」标记前，修改 `src/` 业务代码。
- 为图省事引入 wildcard import（`from module import *`）或绕过类型检查。
- 把动态任务状态 / 进度 / 交接信息写进本文件（AGENTS.md 是长期规则，会过时误导）；进度只进 `docs/specs/<feature>/handoff.md`。

## 4. 人工闸门（Human Gates）

- **规划闸门**：进入实现前，必须先在 `docs/specs/<feature>/plan.md` 末尾的 `## ✅ Human Approval` 区块获得人工勾选。
- **合并闸门**：PR 未经人工 review 不得合并；CI 任一阶段失败即阻断。
- 验收标准以 `spec.md` 的「Acceptance Criteria」为准，**可测**才算完成。

## 5. 规范与路由

- 项目级原则见 `docs/constitution.md`（人 owner 维护）。
- 若采用多 Agent（planner/coder/reviewer/security），人格定义见 `.agents/`，交接协议以 `plan.md` 为书面合同。
- 本文件只放「全局 + 跨工具」规则；单文件类型规则下沉到对应工具的规则文件。

## 6. 质量基线与约定

- TypeScript `strict: true`；函数 ≤ 50 行，文件 ≤ 300 行。
- 提交遵循 Conventional Commits：`feat:` / `fix:` / `refactor:` / `test:` / `docs:`。
- 日志遵循 `docs/logging-framework/INTERFACE.md` 统一接口；Web 实现为 `@scaffold/observability`（`logging-framework/web/Observability`），禁止 `console.log` 作为生产日志手段。
- 前端错误务必经 ErrorBoundary 上报，绝不吞掉异常。

## 7. 进度可交接（Clock-in / Clock-out）— 要点 4

- **核心原则**：任务进度、决策、验证证据必须写入仓库（`handoff.md` / `tasks.md` / Git 提交），**绝不**只活在对话历史里。换 Agent、换工具、换机器都能靠文件续作。
- **Clock-in（开工）**：读 `docs/specs/<feature>/handoff.md` → 读 `docs/decisions/` → `git log --oneline -10`，确认当前状态再从 `handoff.md` 的「Next Steps」继续。
- **Clock-out（收工，IMPORTANT）**：更新 `handoff.md`（已完成 / 阻塞 / 下一步 / 已跑命令与结果）→ 跑通 `pnpm lint && pnpm typecheck && pnpm test` → 提交 `chore: state checkpoint`。
- **验证门禁**：测试未全绿前，不得把 `tasks.md` 该项标记为 done，不得声称完成。
- 并行多 Agent 时，每个任务在独立 git worktree 开发，主仓库保持干净，互不污染。

## 8. 强制约束层（机器守门，不止是文档）— 要点 3 落实

> 上面的规则若只靠自觉，AI 完全可以「假装读过、不遵守」。本仓库用三层**硬门禁**把约束变成机器强制：

1. **Git Hooks（husky，对 Ded 任何工具都生效）**：`pre-commit` 拦截 `.env`/密钥 + 跑 ESLint（含 `no-console` 硬错误）；`commit-msg` 强制 Conventional Commits；`pre-push` 跑通 `typecheck`+`test`。
2. **Agent Hooks（Claude Code：`.claude/settings.json` + `scripts/hooks/*.mjs`）**：改 `src/` 前必须存在已批准 `plan.md`（`check-plan.mjs` 直接 `exit 2` 阻断）；拦截高危 Bash 命令（`guard-bash.mjs`）；改完即跑 ESLint 自纠（`lint-touched.mjs`）。
3. **CI（远端）**：两个 job——`quality`（经中立 `tooling/gate-runner.mjs` 跑 lint/typecheck/test/构建）+ `security`（gitleaks 密钥扫描 + `pnpm audit --prod`），任一失败即阻断合并。门禁的实际执行由 `gate-runner` 统一驱动（发现 `.toolchain.json` → 按适配器跑各阶段），详见 `docs/gate-contract.md`。

- 紧急绕过（需人工知晓并事后补规则）：`SKIP_PLAN_CHECK=1` / `SKIP_BASH_GUARD=1`；绕过会被记入日志，不可滥用。
- 详见 `DESIGN.md` §7「强制约束层」与各 Hook 脚本注释。
