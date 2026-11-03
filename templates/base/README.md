# {{PROJECT_NAME}}

> 由 `ai-dev-spec` 脚手架生成的语言中立项目骨架。
> 本仓库的**契约与门禁是语言无关的**——具体语言工具由 `tooling/adapters/*` 适配。

## 目录结构

```
.
├── .agent/                 # Agent 约束（语言中立）
├── config/
│   ├── logging.config.json       # 语言中立的日志配置（所有语言读同一份）
│   └── logging.config.schema.json
├── docs/
│   ├── constitution.md           # 项目宪法（人类 owner 维护）
│   ├── spec-format.md            # 特性规范格式（语言无关）
│   ├── gate-contract.md          # 中立门禁契约
│   └── logging-framework/
│       ├── INTERFACE.md          # 统一日志接口规范
│       └── schema/log-event.schema.json  # 线格式契约（Schema v1 真源）
├── tooling/                # 中立门禁执械（gate-runner + 适配器 + hooks）
└── .toolchain.json         # 声明本模块用哪种适配器（lint/typecheck/test/build）
```

## 两种用法

- **初始化新项目**：`node <scaffold>/tooling/init.mjs <lang> ./my-app`
- **为已有项目追加约束+日志**：`node <scaffold>/tooling/add-to-existing.mjs <lang> ./existing`

## 日常门禁

```bash
node tooling/gate-runner.mjs                 # 跑全部模块的 lint/typecheck/test/build
node tooling/gate-runner.mjs --stages lint   # 只跑指定阶段
```

门禁发现机制：扫描所有含 `.toolchain.json` 的目录 → 按 `adapter` 加载 `tooling/adapters/<adapter>.mjs`
→ 把 `lint/typecheck/test/build` 翻译成该语言的真实命令并执行。**新增一门语言 = 新增一个适配器文件，其余零改动。**

## 日志

所有 logger 必须 conform `docs/logging-framework/INTERFACE.md`，输出满足
`docs/logging-framework/schema/log-event.schema.json`（snake_case 线格式、6 档 level）。
配置统一读 `config/logging.config.json`。
