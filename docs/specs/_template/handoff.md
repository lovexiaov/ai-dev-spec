# HANDOFF: <特性名称>

> 连续性凭证：每个特性一份，每次收工更新。新 Agent 启动第一件事就是读它。
> 状态只进仓库、不进聊天历史——换 Agent / 换工具 / 换机器都能靠本文件续作（要点 4）。

## Goal（本次目标）
- 一句话说明「做完」的判定，以及绝不能改的东西。

## Current State（当前状态）
- Branch: `feat/xxx`  Last commit: `<hash>`
- 正在做：T? —— 进度 __% ；跑得起来 / 跑不起来。
- 测试：`pnpm test` → __ passed / __ failed（附失败项）。

## What Changed（已改动）
- `src/...` (new | modified)：做了什么。

## Commands Run & Results（已跑命令与结果）
```bash
pnpm test -- -t "reset-request"  # → 5 passed
pnpm typecheck                   # → ok
```

## Decisions & Why（决策与理由）
- 选 X 而非 Y，因为……（重要决策沉淀，避免后人重蹈覆辙）。

## Next Steps（下一步）
1. ……
2. ……

## Blockers / Open Questions（阻塞与待解）
- ……

## How to Verify（如何验证）
```bash
pnpm lint && pnpm typecheck && pnpm test
```
