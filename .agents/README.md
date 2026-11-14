# .agents/ — 多 Agent 人格与交接协议

> 本目录落地 `DESIGN.md` 要点 3/4：把 planner / coder / reviewer / security 拆成独立人格文件，
> 交接以 `docs/specs/<feature>/plan.md` 为书面合同。**全局规则仍以根目录 `AGENTS.md` 为准**；
> 这里只写「某角色怎么干活」，不重复三层边界、人工闸门、Clock-in/Out 的通用定义。

## 何时启用

- 单 Agent 顺序完成小任务：不必加载人格，按 `AGENTS.md` 执行即可。
- 需要**写/审分离**、并行开发、或跨会话接力：按角色加载对应文件，每个角色使用独立上下文。
- 并行时每个任务在独立 git worktree 开发，主仓库保持干净（`AGENTS.md` §7）。

## 角色矩阵

| 角色     | 文件          | 可写范围                                                       | 出口条件                                       |
| -------- | ------------- | -------------------------------------------------------------- | ---------------------------------------------- |
| planner  | `planner.md`  | `docs/specs/<feature>/{spec,plan,tasks}.md`、`docs/decisions/` | `plan.md` 的 `## ✅ Human Approval` 已被人勾选 |
| coder    | `coder.md`    | `src/`、`tests/`、`tooling/`、六端 SDK 子仓                    | 门禁全绿 + `handoff.md` / `tasks.md` 已更新    |
| reviewer | `reviewer.md` | **只读**（只输出审查意见，不改代码）                           | 给出 `block` / `nits` / `pass` 结论            |
| security | `security.md` | **只读 + 阻断权**                                              | 密钥 / 依赖 / 不可逆操作清单无红色项           |

## 交接协议（书面合同 = `plan.md`）

1. **planner** Clock-in → 起草 `spec.md` / `plan.md` / `tasks.md` → 人在 `plan.md` 末尾勾选批准 → Clock-out。
2. **coder** Clock-in（读 `handoff.md` → `docs/decisions/` → `git log --oneline -10`）→ 一次只做一个 `tasks.md` 原子项 → 提交 → Clock-out 更新 `handoff.md` / `tasks.md`。
3. **reviewer** 用干净上下文审 Diff（禁止自审）；结论写回 `handoff.md` 的 Review 段。
4. **security** 在涉及发布、依赖、密钥、workflow 的改动前过一遍；发现红色项立即阻断。
5. 任何角色都**不把状态只留在对话里**：进度、决策、验证证据必须写入仓库（constitution §2.6）。

## 跨角色硬约束

- **规划闸门**：`plan.md` 未含 `## ✅ Human Approval` 勾选，coder 禁止改 `src/`；`scripts/hooks/check-plan.mjs` 会硬拦（`exit 2`）。
- **合并闸门**：CI 任一阶段失败即阻断；测试未全绿不得把 `tasks.md` 标为 done、不得声称完成。
- **不可逆 / 对外可见**（发布、tag 重指、force push、删除数据、外发消息）必须人工确认。
- 提交遵循 Conventional Commits；改 `.github/workflows/` 需人工 review（`AGENTS.md` §3 NEVER）。
- 跨工具规则见 `AGENTS.md` / `CLAUDE.md` / `.cursor/rules/project.mdc`；可复用的自动流程见 `.workbuddy/skills/`。

## 维护约定

- 人格文件与 `AGENTS.md` 一样遵守「伤疤」原则：只写会改变 Agent 行为的项目特有事实，不堆通用常识。
- 新增角色时同步更新本表与 `AGENTS.md` §5 路由；规则冲突时以 `AGENTS.md` 为准。
