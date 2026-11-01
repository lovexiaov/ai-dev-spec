# Tasks: <特性名称>

> 任务要拆到「Agent 能稳定执行」的粒度：改哪些文件 + 跑哪些验证 + 完成判定。
> 每项带 **状态** 与 **验证证据**，便于随时换 Agent 接手（要点 4）。
> - 状态：`todo` / `in_progress` / `blocked` / `done`
> - 证据：`Verified`(真实跑通) / `Proxy`(类型/lint/单测间接证明) / `Not run`(未执行)
> 收工时把进度同步进 `handoff.md` 并提交 checkpoint（见 AGENTS.md §7）。

## 任务清单
- [ ] **T1** 在 `src/services/auth.ts` 新增 `requestReset(email)`
  - 状态：todo | 证据：Not run
  - 验证：`pnpm test -- -t "reset-request"`
  - 判定：返回 202 且不枚举用户
- [ ] **T2** 在 `src/services/auth.ts` 新增 `confirmReset(token, password)`
  - 状态：todo | 证据：Not run
  - 验证：`pnpm test -- -t "reset-confirm"`
  - 判定：过期 410 / 复用 400 / 复杂度不满足 400
- [ ] **T3** 为上述两接口补集成测试，覆盖 spec 的 5 条验收条件
  - 状态：todo | 证据：Not run
  - 判定：`pnpm test` 全绿
- [ ] **T4** 在 `confirmReset` 全链路注入 `traceId`（复用 `@scaffold/observability`）
  - 状态：todo | 证据：Not run
  - 判定：日志中出现一致 `traceId`
- [ ] **T5** 更新本文档与本特性 `spec.md` 的 Done-when
  - 状态：todo | 证据：Not run
  - 判定：`pnpm lint && pnpm typecheck` 通过

## 完成标准
- 所有验收测试通过；lint/typecheck/test 全绿；PR 描述含命令与结果；人工 review 通过。
- 测试未全绿前，任何项不得标记 done（验证门禁，对应 AGENTS.md §7）。
