# Spec Format（特性规范格式）

> **语言无关**。每个特性一份 `docs/specs/<feature>/spec.md`，是 Agent 与人类的「书面合同」。

## 模板

```markdown
# <feature> 规范

## Goal

一句话说明要解决什么问题、为谁解决。

## Non-goals

明确**不**做什么，避免范围蔓延。

## Constraints

硬性约束：性能、合规、依赖、平台、数据保留期等。

## Interfaces

对外契约：API / 配置 / 事件 / Schema 字段。
引用 `docs/logging-framework/schema/log-event.schema.json` 等中立契约。

## Acceptance Criteria（可测）

用 Given/When/Then 或清单列出可自动验证的验收点。**不可测的不算完成。**

## Done-when

完成的定义（通常 = Acceptance Criteria 全绿 + 文档同步）。

## Open Questions

待决策项。
```

## 约定

- 路径固定 `docs/specs/<feature>/`；同目录可放 `plan.md`（实现规划，需人工 Approval）、`handoff.md`（进度交接）。
- 验收必须由 `gate-runner` 的 `test` 阶段覆盖，不能只靠人工目测。
- 改动 API / Schema / `docs/constitution.md` 硬性约束前，须走 AGENTS.md 的 ASK FIRST 闸门。
- 本格式不绑定任何实现语言：无论用 TypeScript、Swift、Python 还是 Go，spec 都长这样。
