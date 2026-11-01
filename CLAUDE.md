@AGENTS.md

# Claude Code 专属补充
- 进入任何代码变更前，先运行 `pnpm lint && pnpm typecheck` 自检。
- 使用 Plan Mode 处理 `src/` 下的改动，待 `plan.md` 获人工批准后提交 Implement。
- 优先用子 Agent 做「写/审分离」：让一个干净上下文的 reviewer 子 Agent 审 Diff，避免自审偏差。
- 收工前按「Clock-out」更新 `docs/specs/<feature>/handoff.md` 并提交 `chore: state checkpoint`；开工先读 `handoff.md`，确保换 Agent 不断上下文。
- **Agent Hooks 已激活（`.claude/settings.json`）**：本环境的 tool-use 已被机器强制——改动 `src/` 前必须有已批准 `plan.md`（否则被拦截）、高危 Bash 命令被拦、改完即跑 ESLint 自纠。这些是硬门禁，不是建议；遇拦截按提示修复或走 `SKIP_*` 紧急绕过（需人工知晓）。
