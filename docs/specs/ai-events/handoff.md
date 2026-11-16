# HANDOFF: AI 交互事件六端统一（ai-events）

> 连续性凭证：每个特性一份，每次收工更新。新 Agent 启动第一件事就是读它。
> 上游：`spec.md`（契约）、`plan.md`（已人工批准，含 D4「不产 span」决策）、`tasks.md`（逐项状态与证据）。

## Goal（本次目标）

- **做完的判定**：六端（Python / Go / Java / Android / Web / macOS）都能产出 Schema v1.4 的
  标准 AI 交互事件（6 个 `event_type` 值 + snake_case payload 词表），`xlang_verify` 含 AI
  样例且六端 OTLP 一致且**均不产 span**；SDK 版本与 schema 同步升 `1.4.0`，tag 推送、7 仓 CI 全绿。
- **绝不能改的东西**：v1.3 行必须仍然合法（只加不改）；AI 事件为**显式埋点**（`agent_auto=false`），
  不 hook 任何 LLM SDK；OTLP 层只作 log 信号，不产 `Span`（plan.md 决策 D4）；`ai_error`
  复用 v1.3 异常词表；不引入第三方依赖。

## Current State（当前状态）

- Branch: `main`（六子仓 + monorepo 均在 main，工作区干净）
- 进度：**T1–T11 全部 `done`**（证据见 `tasks.md`）。
- 提交：六子仓均 `feat(schema-v1.4): 六端统一 AI 交互事件并发布 1.4.0`（Go 额外
  `style(go): gofmt event.go`，tag 重指到修复提交）；monorepo `984bc30` + `2bbe9c2` + `e7299f6`。
- 发版：六端 annotated tag `v1.4.0` 已推送远端（仅 Git tag，未发 npm/PyPI/Release）。
- CI：**7 仓全绿**（2026-11-11 核对：六子仓 headSha 均为 v1.4.0 指向提交；monorepo
  `e7299f6` run 42863311895 success 2m34s）。此前排队的 macOS arm64 runner 已完成
  （12m38s success），Go gofmt 修复后重跑 success。

## What Changed（已改动）

### 契约层（monorepo）

- `docs/logging-framework/schema/log-event.schema.json` → `version=1.4.0`：`event_type`
  description 增补 6 个标准 AI 值；`required` 未变（纯增量，v1.3 行仍合法）。
- 5 份 schema 副本同步（python/go/java/android 的 `docs/schema/` + `templates/base/docs/`）。
- `docs/logging-framework/INTERFACE.md` 新增 §4.4 AI 事件段（6 值 + 词表 + level + 不产 span）。

### 六端源码（每端同一套落点）

- Python `agentlog/ai_events.py`（`record_ai_*` 6 函数）；Go `logger.go` `RecordAI*` 6 方法
  - `event.go` 6 常量；Java/Android `AiEvents` + `CoreTypes` 6 值 + 门面委托；
    macOS `AiEvents.swift`（`AgentLog` 静态扩展，`record(...)` 改显式 `agentAuto`）；
    Web 保留 `logAi*` 函数名、payload 字段迁移到标准词表并传 `agentAuto: false`。
- 各端 `AiEventTests`：断言 `event_type` ∈ 6 标准值、payload 无 camelCase 别名泄漏、
  `ai_error` 带异常词表且 `level=error`。
- 六端 `CHANGELOG.md` 新增 `[1.4.0] - 2026-11-11`；`README.md` 补 AI 用法（Web 附迁移对照）。

### 一致性工具与版本

- `xlang/samples.json` 9 条样例（+2 条 AI：`ai_response_received` 带 token + `request_id`、
  `ai_error` 带异常词表）；六端 OTLP 适配器把 `ai_error` 纳入 `exception.*` 映射。
- 13 处版本字面量对齐 `1.4.0`（六端 `telemetry.sdk.version` 实测一致，否则 `xlang_verify` 报差异）。

## Commands Run & Results（已跑命令与结果）

| 端      | 命令                                                                 | 结果                                     |
| ------- | -------------------------------------------------------------------- | ---------------------------------------- |
| Python  | `python3 -m unittest discover -s tests -q`                           | 115 tests OK                             |
| Go      | `go test ./...`                                                      | ok                                       |
| Java    | `mvn -o test`                                                        | 66 tests / 0 failures                    |
| Android | `./gradlew :agentlog-core:test :agentlog-core:ktlintCheck --offline` | 61 tests / 0 failures + ktlint 通过      |
| Web     | `pnpm typecheck && pnpm lint && pnpm test`                           | 68 passed                                |
| macOS   | `swiftc -typecheck` + `/tmp/swiftrun` 本地桩                         | 零 error / 70 passed（CI 真跑兜底）      |
| 跨端    | `python3 tools/otlp-compat-verify/xlang_verify.py`                   | EXIT=0（9 样例，5/5 端一致，零 AI span） |

2026-11-11 接管复核（本 Agent 实测）：

```bash
pnpm lint && pnpm typecheck && pnpm test   # 全绿（web 68 passed）
node tooling/gate-runner.mjs               # ✅ 全部门禁通过（python adapter lint+test 115 OK）
gh run list / gh run watch                 # monorepo e7299f6 CI success；六子仓 v1.4.0 全 success
```

## Decisions & Why（决策与理由）

- **不产 span（D4）**：AI 事件在 OTLP 层只作 log 信号（可挂 `span_id` 供下游组 span）。
  经会话内 `AskUserQuestion` 人工批准（2026-11-10）。
- **`agent_auto=false` + 显式埋点**：AI 事件由业务代码经便捷方法产生，区别于 crash/network
  自动埋点；框架不 hook LLM SDK（spec 非目标）。
- **Web 保留 `logAi*` 函数名**：只改 payload 字段为标准词表、明确 level、传 `agentAuto`，
  降低业务侧迁移成本；迁移对照见 Web README。
- **`request_id` 不强制生成**：由调用方传入并跨同轮事件保持一致，框架不造轮子。
- **token 计数用 int**：xlang 校验虽已容忍 int/double，但六端统一 int 消除噪声。
- **Go tag force-update 可接受**：tag 刚发布、无外部消费，gofmt 修复后重指；
  若日后有外部依赖 tag，此操作必须重新评审。

## Next Steps（下一步）

1. **发布渠道决策（未做，等产品判断）**：npm / PyPI / GitHub Release 均未发；账号注册 + 2FA
   只能由人工完成。发布配置已就绪（见下「发布准备状态」）。
2. 下游消费侧可选工作（不在本 spec 范围）：按 `request_id` 聚合「请求→响应→工具→错误」
   轮次视图、AI 事件看板、按 `model`/`provider` 维度统计。
3. 若做 LLM SDK 自动埋点（hook OpenAI/Anthropic 等），需新开 spec——本期明确为非目标。

## 发布准备状态（2026-11-16 更新）

> 完整的人工操作步骤见同目录 **[`RELEASING.md`](./RELEASING.md)**：账号注册 + 2FA、凭据绑定、手动首发命令、
> `wip/release-ci` 恢复步骤、故障速查（含 §0.1 npm 2FA 现状）。本节只记状态快照。

- **PyPI 首发已完成**：`agentlog-py 1.4.0` → <https://pypi.org/project/agentlog-py/1.4.0/>，
  官方源全新安装 + 运行验证通过。python 子仓 `46677f7`，tag `v1.4.0` 已前移到此提交。
- **npm 首发受阻，但**不是**代码或网络问题**：包名定为 `agentlog-js`，构建与打包已就绪
  （`agentlog-js-1.4.0.tgz`，37.1 kB / 35 files，全在 `dist/`），web 子仓 `53c98b4`，tag 已前移。
  卡点是 npm 账号的 2FA 政策链：
  - 2026-11-16 22:50 左右用**恢复码**完成登录 → 触发 npm **72 小时只读冻结**，
    预计 **2026-11-19 22:50 之后**自动解除（无需工单，但**期间不能再动 2FA，否则重置计时**）。
  - 冻结期间 publish / 建 token 全部 `403 temporarily suspended`，只读操作（whoami / view / 安装）正常。
  - 解除后的解锁顺序：① 能打开 `www.npmjs.com`（家宽出口 IP 被 Cloudflare 拦 403，用手机热点换 IP）
    → ② 绑 WebAuthn 安全密钥（Mac 可直接用 Touch ID，npm 已不支持 TOTP 认证器）
    → ③ 在**真实终端**跑 `npm publish`，浏览器弹窗确认。详见 RELEASING.md §0.1。
  - Agent 无法代劳发布：无 TTY 环境会直接 `EOTP` 失败，只读验证（`npm view` + 安装冒烟）可代劳。
- **`release.yml` 未推送（人工挂起）**：各子仓提交了 tag 触发的发布工作流
  （python `ed04461` / web `ca1b97f`），但 push 被 GitHub 拒绝——当前 PAT 缺 `workflow`
  scope（`git` 经 `gh auth git-credential` 取凭据）。这两个提交**保存在各子仓本地分支
  `wip/release-ci`**，未删除、未改写。
- 用户已决定：将来 `release.yml` **只进 main，tag 保持 publish-config 不动**（v1.4.0 手动发布，
  CI 管未来版本）。恢复步骤：给 PAT 加 `workflow` scope → 各子仓
  `git checkout main && git merge wip/release-ci && git push origin main` → monorepo 按需更新指针。
- **submodule 指针一致**：python `46677f7` / web `53c98b4` 均已在远端存在，monorepo 指针为
  `46677f7` / `53c98b4`（提交 `380fead`），全新 `clone --recurse-submodules` 可正常检出。

## Blockers / Open Questions（阻塞与待解）

- spec 验收条件 7 项全部勾选（见 `spec.md` Acceptance Criteria），**无代码阻塞**。
- 外部待解（均为人工操作，挂起中）：
  - **npm 首发**：账号处于 **72 小时安全冻结**（约 `2026-11-19 22:50` 自动解除）。解除后还需
    解决 `www.npmjs.com` 访问（Cloudflare 拦家宽 IP）+ 绑定 WebAuthn 安全密钥，再由人工在
    真实终端发布。操作顺序见 RELEASING.md §0.1。
  - **PAT `workflow` scope**：`release.yml` 推送仍挂起。
  - PyPI 侧无待办（`agentlog-py 1.4.0` 已上线并验证）。

## How to Verify（如何验证）

```bash
# 契约层：六副本 version 一致 = 1.4.0
python3 -c "import json;print(json.load(open('docs/logging-framework/schema/log-event.schema.json'))['version'])"
for d in python/AgentLog go/AgentLog java/AgentLog android/AgentLog; do
  diff -q docs/logging-framework/schema/log-event.schema.json logging-framework/$d/docs/schema/log-event.schema.json
done

# 六端测试 + 跨端一致性（命令见上表）
python3 tools/otlp-compat-verify/xlang_verify.py

# monorepo 门禁
pnpm lint && pnpm typecheck && pnpm test && node tooling/gate-runner.mjs
```
