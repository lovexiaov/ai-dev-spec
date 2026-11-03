# AI 开发脚手架方案（ai-dev-spec）

> 目标：在「人退居需求与决策者、AI Agent 主导编码」的新范式下，用一套可复用的项目初始化脚手架，把四条关键注意点**固化进目录结构、配置文件与核心模块**，让新项目从第一行代码起就自带约束、可观测、验收与进度可交接机制。

> **本脚手架是语言中立（language-agnostic）的**：根仓库只承载「中立契约」（`docs/constitution.md`、`docs/spec-format.md`、`docs/gate-contract.md`、`docs/logging-framework/INTERFACE.md`、`schema/log-event.schema.json`），具体语言工具由 `tooling/adapters/*` 适配；日志线格式由同一份 JSON Schema 约束，与实现语言无关。脚手架自身用 TypeScript 书写只是其「实现语言」，不影响它产出/约束任意语言的项目。

---

## 一、网络调研结论（四要点最佳实践）

### 要点 1：人的角色从「开发者」转变为「需求提供者 + 关键决策者」

- **Spec-Driven Development（SDD，规范驱动开发）** 是 2025–2026 年最共识的实践。核心是把「设计」与「实现」分离：先让 Agent 产出 `spec / plan`，人审完再编码（intent-driven.dev、thoughtworks、Dendro Logic 2026 报告）。
- **角色重定义被多家报告一致确认**：OpenAI / Anthropic / Cursor 三家的 AI 编程指南收敛为同一工作流——`explore → plan → implement → review`，即「规范先行、Agent 实现、人做评审」（mondaymomentum.io《The New Developer Playbook》）。
- **工程师变成「规范架构师 / 技术编辑 / 智能的架构师」**：新核心能力是「写一份对 LLM 无歧义的 spec」，而非写代码；spec 成为评判 Agent 的「契约」与唯一事实来源（zooz.com《The End of Infinite Context》）。哥伦比亚商学院称为「Everyone gets promoted to manager」——非技术管理者也能管理技术 Agent（ai.columbia.edu）。
- **最小规范 + 有意义拆解**：规范要小、可被人类审阅；用 INVEST / MoSCoW 把大特性切成独立可交付的薄片，避免「规范剧场」（写了没人看）与「上下文腐败 / 失忆」（intent-driven.dev）。
- **人的「闸门」不可省略**：Agent 不能未经人工 toggle 就从 Plan 进入 Implement，不能未经人工 review 就合并 PR（zooz.com、Dendro Logic）。

### 要点 2：AI 主导开发时，日志（尤其前端 / Web 这类难单测的应用）格外重要

- **AI 生成代码带来新的可观测性挑战**：结构化日志、分布式追踪、一致的错误处理「不可妥协」（altersquare.io、skills.cat observability skill）。
- **前端要「可观测优先」**：前端通过可观察的 DOM/状态无意中暴露了「隐式 API」，Agent 会去消费它们；一旦出错，人类看不到、Agent 无法「刷新重试」，必须有结构化反馈（techsheet.vercel.app《Resilient Front-End Architectures for the AI-Augmented SDLC》）。
- **结构化日志的字段规范**：生产环境输出 JSON，固定字段统一由 **Schema v1** 定义（见 `docs/logging-framework/schema/log-event.schema.json`）：`ts / level / service / event_type / session_id / agent_auto / message` 必填，`trace_id / subsystem / category / env / user_id / payload` 可选；密钥必须脱敏；开发环境才可读（skills.cat、getlockstep.dev）。
- **前端 AI 交互要记录生命周期事件**：`ai_request_initiated`、`ai_tool_call_initiated/completed`、`ai_response_received`、`ai_guardrail_triggered`、`ai_error`——带 `userId / sessionId / model / tokenUsage`（aivoid.dev 第 13 章）。
- **追踪与指标**：用 OpenTelemetry 打通 frontend → API → DB；RED 指标（Rate/Errors/Duration p50–p99）；前端 + 后端都接 Sentry 并上传 source map；`/health`、`/ready` 健康检查（skills.cat、kwkr.cn 前端转大模型实战）。
- **收益**：投资专业可观测平台后，AI/数据系统宕机时间可降约 80%（altersquare.io）。

### 要点 3：AI 写码快、人工难 review，需约束 AI 行为并明确验收条件

- **三层边界（always do / ask first / never do）** 是成本最低、收益最高的约束写法（completeaitraining.com、codemyspec.com）。
- **Guardrails 清单**：do-not-touch 文件/目录清单、默认只读、升级需审批、小 PR、合并前强制 lint/安全扫描/单测/静态分析、灰度发布 + 回滚路径（completeaitraining.com）。
- **验收条件必须「可测」**：写「过期 token 返回 401」而非「安全地处理鉴权」；可测验收条件是 Agent 自我验证的信号（nomadx.ae、codemyspec.com）。
- **用测试当护栏**：失败测试 = 没做完；让 Agent 在声明完成前先跑测试（nomadx.ae、《The New Developer Playbook》测试驱动一切）。
- **治理文件要短而准**：`AGENTS.md` / `CLAUDE.md` 作为全局「宪法」，控制在 ~200 行以内，只写「它自己发现不了的信息」与「不要做什么」（getlockstep.dev、agents.md 规范、掘金《AI Agent 驾驭指南》）。
- **模块化人格 + 交接协议**：把 planner / coder / reviewer / security 拆成 `.agents/` 子文件，明确交接时把决策写入 `plan.md`，coder 在 `plan.md` 含人工批准标记前不得改源码（thinkinginsidethebox.ai）。
- **写 / 审分离**：让独立上下文的 reviewer（人或子 Agent）审代码，避免「自己审自己」的偏差（Dendro Logic）。
- **小原子迭代**：一次给 Agent 太多任务会产出「十个没沟通的开发者写的东西」（Osmani 经验，Dendro Logic）。

### 要点 4：Agent 工作进度要可观测、可跟踪、可随时换人接手

- **核心原则：状态外置到仓库，而非对话历史**：跨会话 / 跨 Agent 接力的本质是「外部状态接力」，不是「会话接力」。把关键决策只留在聊天历史里，换 Agent 后必然丢上下文；把任务状态放进仓库、Git、测试与结构化交接文档，新 Agent 才能在不同终端 / IDE / 机器间无缝续作（aistacknav.com《Claude Code+Codex 跨平台任务接力》）。
- **HANDOFF / PROGRESS 文档即连续性凭证**：每个特性维护一份 `handoff.md`，记录目标、当前状态、已完成且已验证的工作、阻塞项、下一步、改动文件、已跑命令与结果、关键决策（docs-md.com、strangelove-ai.com、walkinglabs.github.io）。新 Agent 启动时第一件事就是读它——把「重建上下文」成本从 15 分钟压到 3 分钟。
- **Git 提交即检查点**：每次完成原子工作就提交，commit message 写成结构化交接笔记（实现了什么 / 哪些测试通过 / 下一个待办）；`git log` 成为人机可读的进度审计链（agentpatterns.ai、walkinglabs）。
- **Clock-in / Clock-out 例程写进 AGENTS.md**：上班先读 `handoff.md / decisions / git log`；下班前更新 `handoff.md`、跑通校验、提交 `state checkpoint`（strangelove-ai.com）。
- **任务列表带机器可读状态**：`tasks.md` 每项带 `todo / in_progress / blocked / done` 状态与「验证证据」（Verified / Proxy / Not run），交接报告可据此自动生成（zylos.ai、minimal-harness AGENTS.md）。未完成测试前，`passes` 不得翻为 true。
- **进度也要进日志（可观测）**：用 `agent_step` / `agent_handoff` / `agent_decision` 等事件把「Agent 在做什么、做到哪了、为什么换人」写进同一套结构化日志，使进度不仅有人读的文件、也有机查的流（呼应要点 2 的可观测底座）。
- **Worktree 隔离并发**：多 Agent 并行时，每个任务在独立 git worktree 开发，主仓库保持干净，互不污染（jxxy.net《Agent 工程师是怎么用 AI 写代码的》）。

---

## 二、脚手架总体设计原则

1. **规范先于代码**：`docs/` 下的 `constitution → spec → plan → tasks` 是一条人工闸门链，对应要点 1 与要点 3 的「人决策」节点。
2. **约束写进治理文件，强制写进三层机器门禁**：`AGENTS.md` 给 Agent 看（软约束），真正拦人的是三层**硬门禁**——① `Git Hooks`（husky：pre-commit / commit-msg / pre-push，对 Ded 任何 AI 工具都生效）② `Agent Hooks`（`.claude/settings.json`：tool-use 前/后置拦截）③ `.github/workflows/ci.yml`（远端 PR 闸门）。软硬必须一致，避免「文档写得好、AI 不遵守」的空转。
3. **可观测性即一等公民**：可观测性不是一个「以后再加」的模块，而是独立仓库维护、以 submodule 挂入的 `logging-framework/web/Observability`（`agent-log-web`）核心包，前端 / 后端开箱即用，对应要点 2。
4. **验收条件即测试**：`spec.md` 的验收清单与 `tests/` 一一对应，Agent 跑不过测试就不算完成。
5. **状态外置、进度可交接**：任务进度、决策、验证证据必须写入仓库（`handoff.md` / `tasks.md` / Git 提交），而非对话历史；任何新 Agent 读文件即可恢复上下文继续干活，对应要点 4。

---

## 三、目录结构

```text
ai-dev-spec/                         # 脚手架根（= 你的项目根）
├── README.md                       # 给人类：项目说明 + 四原则速览 + Hooks 安装
├── AGENTS.md                       # 【要点3】全局治理：约束、命令、三层边界、人工闸门（≤200 行）
├── CLAUDE.md                       # 软链/导入 AGENTS.md（Anthropic 系工具兼容）
├── .cursor/rules/project.mdc       # Cursor 系兼容：指向 AGENTS.md
│
├── package.json                    # 根工程：pnpm workspace + scripts(dev/build/test/typecheck/lint/format/prepare)
├── pnpm-workspace.yaml             # 工作区声明（含 logging-framework/web/Observability 子模块作为成员）
├── tsconfig.base.json             # 共享 TS 严格配置（strict/noUncheckedIndexedAccess…）
├── eslint.config.js               # 【强制】ESLint 扁平配置，含 no-console 等硬错误
├── commitlint.config.js            # 【强制】commit message 规范（Conventional Commits）
├── .lintstagedrc.json             # lint-staged 配置（pre-commit 触发）
├── .npmrc / .gitignore            # pnpm 配置 / 忽略 .env 等
├── .gitmodules                    # 两个 submodule：agent-log-web、agent-log-macos
│
├── .husky/                        # 【强制·Git Hooks】本地第一道硬门，覆盖任何 AI 工具
│   ├── pre-commit                 # 密钥/.env 拦截 + secret 扫描 + lint-staged（eslint 强制）
│   ├── commit-msg                 # commitlint 强制 Conventional Commits
│   └── pre-push                   # typecheck + test 必须全绿
├── .claude/
│   └── settings.json              # 【强制·Agent Hooks】Claude Code tool-use 前/后置拦截（参考实现）
├── scripts/
│   └── hooks/                     # Agent Hook 脚本（Node，跨平台）
│       ├── check-plan.mjs         # 改 src/ 前必须有已批准 plan.md（PreToolUse 拦截）
│       ├── guard-bash.mjs         # 拦截高危/不可逆 Bash 命令（PreToolUse 拦截）
│       └── lint-touched.mjs       # 改完即跑 eslint 强制自纠（PostToolUse）
│
├── docs/                           # 【要点1】规范先于代码
│   ├── constitution.md             # 项目级「宪法」：原则、技术栈、不可违反的硬约束
│   ├── logging-framework/          # 语言无关的日志接入规范（Schema v1 真源）+ 机器可校验 schema
│   │   ├── README.md               # 通用约束与映射表
│   │   └── schema/{log-event.schema.json,example.json}
│   ├── specs/                      # 每个特性一个目录，spec 随代码版本化
│   │   └── _template/              # 复制此目录开始一个新特性
│   │       ├── spec.md            # 目标/非目标/约束/接口/【可测验收条件】/完成定义
│   │       ├── plan.md            # 架构设计，含「✅ 人工批准」标记（要点1 闸门）
│   │       ├── tasks.md           # 原子、可测、带状态/证据的清单（要点3+4）
│   │       └── handoff.md         # 【要点4】交接文档：进度/阻塞/下一步/已跑命令结果
│   └── decisions/                 # ADR 式决策记录（为什么这么做）
│
├── logging-framework/              # 【要点2】可观测核心包：两个独立仓库，以 git submodule 挂入
│   ├── web/Observability/          # submodule → agent-log-web（npm 包名 @scaffold/observability）
│   │   ├── src/logger.ts           # 结构化 JSON 日志 + 脱敏 + traceId（LogEvent 即 Schema v1 线格式）
│   │   ├── src/trace.ts            # traceId 生成与跨调用传播（W3C traceparent）
│   │   ├── src/metrics.ts          # RED 指标 + /health、/ready 辅助
│   │   ├── src/agent-events.ts     # 【要点4】agent_step/handoff/decision 进度事件
│   │   ├── src/frontend/           # ErrorBoundary + 浏览器结构化上报 + ai-events
│   │   ├── src/logger.test.ts      # Schema v1 形状守卫（6 用例）
│   │   ├── package.json / eslint.config.js / tsconfig*.json / pnpm-*.yaml / README.md
│   │   └── （独立仓库维护，@scaffold/observability 接入方 import 路径不变）
│   └── macos/AgentLog/             # submodule → agent-log-macos（Swift + SPM）
│       ├── Package.swift           # swift-log + Pulse + KSCrash，自动埋点（UI/网络/崩溃/卡顿）
│       ├── Sources/AgentLog/*.swift
│       ├── Tests/AgentLogTests/*.swift   # 埋点触发 + Schema v1 断言
│       └── Docs/macos-agent-logging-design.md  # macOS 端设计真源
│
├── config/
│   └── logging.config.ts          # 日志级别、脱敏字段、sink（stdout/Sentry）配置
│
├── src/                           # 业务代码（Agent 主要工作区；受 check-plan Hook 强制门禁）
├── tests/                         # 【要点3】验收条件的可执行载体
│
└── .github/
    └── workflows/
        └── ci.yml                 # 【要点3】远端硬性闸门：quality(lint/typecheck/test/构建) + security(gitleaks + audit)
```

---

## 四、关键配置文件说明

### 1. `AGENTS.md`（全局治理 / 软约束）— 要点 3

- **Project Overview & Commands**：技术栈、构建/测试/lint 命令（Agent 自己发现不了的，才写）。
- **Negative Constraints**：`NEVER 提交密钥`、`.env 不入库`、`legacy/ 目录禁止改动`、`非本包文件删除前先问`。
- **三层边界（Three-tier）**：`ALWAYS` / `ASK FIRST` / `NEVER` 显式分区，把「别做什么」讲清楚。
- **Human Gates**：声明「进入 plan 前必须先读 `docs/specs/<feature>/spec.md`；`plan.md` 未含人工批准标记前不得改 `src/`」——把要点 1 的「人决策」节点硬编码进 Agent 行为。
- **Routing**：指向 `docs/constitution.md` 与 `.agents/` 人格（如采用多 Agent），保持本文件精简。

### 2. `docs/constitution.md`（项目宪法）— 要点 1 + 3

- 记录不可谈判的原则（如「所有外部调用必须带 traceId」「前端错误必须上报 Sentry」「PR 必须小」）。
- 与 `AGENTS.md` 的区别：AGENTS.md 是「怎么跟 Agent 协作」，constitution 是「这个项目信奉什么」，由人owner 维护。

### 3. `docs/specs/_template/*`（特性规范三件套）— 要点 1 + 3

- `spec.md`：Goal / Non-goals / Constraints / Interfaces / **Acceptance Criteria（可测）** / Done-when。
- `plan.md`：只写本次实现真正用到的设计决策（模块边界、数据流、必须 break 的旧路径），末尾留 `## ✅ Human Approval` 区块。
- `tasks.md`：每个任务拆到「改哪些文件 + 跑哪些验证命令 + 完成判定」，可勾选。

### 4. `config/logging.config.ts`（可观测配置）— 要点 2

- 集中定义日志级别、脱敏字段路径（如 `password/token/authorization`）、sink（stdout / Sentry / 远端日志服务）、是否在浏览器端采样。

### 5. `.github/workflows/ci.yml`（硬性闸门）— 要点 3

- PR 触发两个 job：`quality`（lint → typecheck → 单元测试（含 spec 验收测试）→ 构建）、`security`（gitleaks 密钥扫描 + `pnpm audit --prod`）。
- 任一失败即阻断合并，等价于把「人工 review 难」转成「机器先守门」。

### 6. `docs/specs/<feature>/handoff.md`（交接文档）— 要点 4

- 每个特性一份，记录：目标 / 当前状态 / 已完成且已验证的工作 / 阻塞项 / 下一步 / 改动文件 / 已跑命令与结果 / 关键决策。
- **Clock-in 例程**：新 Agent 启动时先读 `handoff.md` + `docs/decisions/` + `git log` 再动手。
- **Clock-out 例程**：下班前更新 `handoff.md`、跑通 `pnpm lint && pnpm typecheck && pnpm test`、提交 `chore: state checkpoint`。
- 动态任务状态**只**放这里，**绝不**写进 `AGENTS.md`（那是长期规则，会过时误导）。

### 7. 强制约束层（Git Hooks + Agent Hooks）—— 让「软约束」变成「硬门禁」

> 设计反思（见本文「review 结论」）：原脚手架只有 `AGENTS.md`（软）+ 远端 CI（硬但仅 PR 触发），
> 本地开发阶段 AI 完全可以「假装读过规则、不填 spec、不改 plan 就改 src/」而**无人拦**。
> 本层把要点 3 的约束从「文档建议」升级为「机器强制」，分三道本地硬门：

**① Git Hooks（husky）—— 对任何 AI 工具都生效的本地第一道门**

- `.husky/pre-commit`：拦截 `.env`/密钥文件与密钥内容（兜底 AGENTS.md NEVER）→ 跑 `lint-staged`（ESLint 含 `no-console` 强制 + Prettier 格式化）。
- `.husky/commit-msg`：`commitlint` 强制 Conventional Commits（feat/fix/...）。
- `.husky/pre-push`：`pnpm typecheck && pnpm test` 必须全绿；并提醒未更新 `handoff.md` 的分支。
- 之所以放 Git 层：**不依赖具体 Agent 工具**——无论 Claude / Cursor / WorkBuddy / 人，只要 `git commit` 就会被拦。

**② Agent Hooks（`.claude/settings.json` + `scripts/hooks/*.mjs`）—— 在 tool-use 层面拦截**

- `PreToolUse` on `Edit|Write|MultiEdit` → `check-plan.mjs`：改 `src/` 前，仓库内必须存在**已勾选 ✅ 批准**的 `plan.md`；否则直接 `exit 2` 阻断并给出修复步骤（紧急绕过 `SKIP_PLAN_CHECK=1`）。
- `PreToolUse` on `Bash` → `guard-bash.mjs`：拦截 `rm -rf /`、`git push --force`、`git reset --hard`、`git clean -fdx`、`sudo`、fork-bomb 等不可逆/高危命令。
- `PostToolUse` on `Edit|Write|MultiEdit` → `lint-touched.mjs`：每改完一个代码文件立刻跑 ESLint，把错误暴露给 Agent 迫使其当场自纠（ESLint 未装时优雅跳过）。
- 注：此处以 **Claude Code 的 hook 格式** 为参考实现；Cursor 暂无等价命令钩子，靠 Git Hooks + rules 兜底；WorkBuddy 钩子由环境托管，逻辑可平移。

**③ 根工程配置让约束「可执行」**

- `package.json` 提供 `lint/typecheck/test` 脚本载体（此前缺失，导致 CI 里的 `pnpm lint` 是空壳；`test` 现已内置 `--bail`）。
- `eslint.config.js` 把「禁止 console.log 做生产日志」落成 `no-console: error`（仅放行 `warn/error` 兜底），`commitlint.config.js` 落 commit 规范，`tsconfig.base.json` 兜底 TS 严格。
- 前端可观测代码（含 `ErrorBoundary`、浏览器 logger、`ai-events`）现位于 submodule `logging-framework/web/Observability/src/frontend/`，其中唯一的 `console.log` 是浏览器无端点时的最后兜底，已用 `eslint-disable` 显式标注。

**强制力对照（与原方案相比）**

| 约束内容（来自 AGENTS.md / constitution） | 原实现                 | 现在如何强制                                                   |
| ----------------------------------------- | ---------------------- | -------------------------------------------------------------- |
| 禁 `console.log` 做生产日志               | 仅文档                 | ESLint error + lint-staged（pre-commit）+ PostToolUse 实时拦截 |
| 提交前跑 lint/typecheck/test              | 仅文档                 | pre-commit（lint-staged）+ pre-push（typecheck+test）          |
| Conventional Commits                      | 仅文档                 | commit-msg hook（commitlint）                                  |
| NEVER 提交密钥/.env                       | 仅文档 + 远端 gitleaks | pre-commit 本地拦截（文件 + 内容扫描）+ 远端 gitleaks 双保险   |
| 改 src/ 前需 plan 批准                    | 仅文档（可自欺）       | Agent Hook PreToolUse 直接阻断                                 |
| 不可逆命令需人确认                        | 仅文档                 | Agent Hook PreToolUse 直接阻断                                 |
| 进度写 handoff                            | 仅文档                 | pre-push 提醒 + 仍建议 AGENTS.md §7 Clock-out                  |

---

## 五、核心模块设计：Web 可观测包 `@scaffold/observability`（要点 2 落地）

设计目标：让前端 / 后端在 AI 主导开发下「看得见、追得清、可回放」。

1. **统一结构化日志（`logger.ts`）**
   - 输出固定字段（Schema v1 线格式，snake_case）：`ts, level, service, event_type, session_id, agent_auto, message` + 可选 `trace_id / subsystem / category / env / user_id / payload`。`LogEvent` 类型即线格式，调用侧仍用 `event / traceId / userId` 等 camelCase 书写，由 logger 在序列化边界映射。
   - 内置脱敏处理器：在 logger 层拦截 `password/token/authorization/PII` 字段，绝不依赖调用方自觉。
   - 日志走 stdout（容器/平台采集），生产为 JSON、开发为可读文本。
2. **追踪传播（`trace.ts`）**
   - 在边缘（网关 / API 入口）生成或接受 `X-Request-ID` / W3C `traceparent`，注入每一行日志并向下游传递；前端经 WebSocket/SSE 回传进度，让用户「感知机器在工作」（呼应 kwkr.cn 实践）。
3. **前端可观测（`frontend/`）**
   - `ErrorBoundary` 捕获渲染崩溃，向 Sentry/日志服务上报，附 `traceId` 与组件栈。
   - 浏览器端结构化 logger，复用后端同一套字段。
   - `ai-events.ts` 专门记录 AI 交互生命周期（对应 aivoid.dev 五类事件），便于事后复盘「Agent 到底干了什么」。
4. **指标与健康（`metrics.ts`）**
   - 暴露 RED 指标；提供 `GET /health`（存活）、`GET /ready`（依赖可达）端点模板，接入外部 uptime 监控。
5. **Agent 进度可观测（`agent-events.ts`）— 要点 4 落地**
   - `logAgentStep` / `logAgentHandoff` / `logAgentDecision`：把「Agent 正在做哪一任务、进度百分比、为何换人、做了什么决策」以结构化事件写入同一套日志（带 `traceId`）。
   - 进度从此既有人读的交接文档（`handoff.md`），也有机查的日志流，满足「可观测、可跟踪、可随时换人」。

> 该包刻意保持「零业务依赖、可独立安装」，任何新项目 `pnpm add @scaffold/observability` 即可获得上述能力。

---

## 六、三要点 → 脚手架落实映射表

| 关键注意点                   | 脚手架落点                                                     | 对应文件 / 模块                                                                                                                                                                                                   |
| ---------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. 人=需求提供者+决策者      | 规范先于代码 + 人工闸门                                        | `docs/specs/_template/{spec,plan,tasks}.md`、`AGENTS.md` 的 Human Gates、`constitution.md`                                                                                                                        |
| 2. 日志 / 可观测（尤其前端） | 自带可观测核心包                                               | `logging-framework/web/Observability/`（submodule）、`config/logging.config.ts`、CI 中的构建/类型门禁                                                                                                             |
| 3. 约束 AI + 明确验收        | 软约束(治理文件)+**三层硬门禁**(Git/Agent Hooks + CI)+可测验收 | `AGENTS.md`(三层边界)、`eslint.config.js`/`commitlint.config.js`(规则落地)、`.husky/`(Git Hooks)、`.claude/settings.json`+`scripts/hooks/`(Agent Hooks)、`.github/workflows/ci.yml`、`tests/`、`spec.md` 验收清单 |
| 4. 进度可观测/可跟踪/可换人  | 状态外置+交接文档+Git检查点+Clock例程+进度日志                 | `docs/specs/<feature>/handoff.md`、`tasks.md`(状态/证据)、`AGENTS.md`(Clock-in/out)、`logging-framework/web/Observability` 的 `agent-events.ts`、Git 提交信息                                                     |

---

## 七、落地建议

1. **以本仓库为模板**：新项目 `git clone --recurse-submodules` 后删掉 `docs/specs/_template` 之外的内容，保留模板与 `logging-framework/` 下的可观测子模块。
2. **先写 constitution，再写第一个 spec**：强制走 `spec → plan(人批) → tasks → 实现` 四步。
3. **AGENTS.md 当「伤疤」写**：每次 Agent 犯错的纠正，沉淀成一条规则；超过 200 行就下沉到 `docs/` 或 `.agents/`（getlockstep.dev 的维护哲学）。
4. **可观测先接入再写功能**：项目第一天就把 `observability` 接上 Sentry/stdout，避免「上线才崩、查无日志」。
   4.5. **强制约束靠 Hooks 生效**：`git clone --recurse-submodules` 后执行 `corepack enable && pnpm install`，husky 自动激活三道 Git Hooks；使用 Claude Code 会自动加载 `.claude/settings.json` 的 Agent Hooks。此后「禁 console.log / 必须 plan 批准才改 src / 高危命令拦截」都是机器守门，AI 绕不过。
5. **小 PR + 机器守门**：把 review 负担从「人肉眼 Diff」转移到「CI 强制 + reviewer 子 Agent 二审」，人只管「意图与边界」。
6. **每次收工即交接**：强制 Clock-out——更新 `handoff.md` + 提交 checkpoint。这样随时能换一个新 Agent（或换工具 / 换机器）接手，上下文零丢失；并行任务用 git worktree 隔离。

---

### 主要参考来源

- intent-driven.dev《Best Practices for Spec-Driven Development》
- mondaymomentum.io《The New Developer Playbook》(OpenAI/Anthropic/Cursor 共识)
- zooz.com《The End of Infinite Context: Engineering Reliability in the Age of Agentic Workflows》
- ai.columbia.edu《When AI takes over coding, everyone gets promoted to manager》
- dendro-logic.com《AI Agents in Development Teams: A Practical Playbook》(2026)
- nomadx.ae《Spec-Driven Development: The Spec Is the New Code (2026)》
- completeaitraining.com《Write Smart Specs, Manage Your AI Intern》
- codemyspec.com《Your AI Agent Is Only as Good as Your Spec》
- agents.md 规范 / getlockstep.dev《AGENTS.md: What to Leave Out》
- techsheet.vercel.app《Resilient Front-End Architectures for the AI-Augmented SDLC》
- aivoid.dev《Chapter 13: Observability from the UI》(2026)
- skills.cat observability skill；altersquare.io；kwkr.cn 前端转大模型实战
- 要点 4（进度可交接）：agentpatterns.ai《Agent Harness》、walkinglabs.github.io《Keeping Context Alive Across Sessions》、strangelove-ai.com《Harness Engineering》、docs-md.com《HANDOFF.md》、aistacknav.com《Claude Code+Codex 跨平台任务接力》、zylos.ai《Context Rotation and Session Handoff》、jxxy.net《Agent 工程师是怎么用 AI 写代码的》、deska.dev《Agent Session Handoff》
