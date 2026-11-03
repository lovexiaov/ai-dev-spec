# Gate Contract（中立门禁契约）

> **语言无关**。本契约定义「一个模块如何向脚手架声明自己的质量门禁」，与具体语言/工具解耦。
> 配套实现见 `tooling/gate-runner.mjs` 与各语言适配器 `tooling/adapters/*.mjs`。

## 1. 核心思想

脚手架只认识**契约**，不认识任何语言工具（`eslint` / `tsc` / `swift` / `pytest` 等）。
每个「模块」（任何含 `.toolchain.json` 的目录）必须声明：

- 用哪个**适配器**（adapter）来翻译门禁命令
- 暴露 4 个标准阶段（stage）：`lint` / `typecheck` / `test` / `build`

`gate-runner` 遍历所有模块，按适配器把每个 stage 翻译成该语言的真实命令并执行。
**新增一门语言 = 新增一个适配器文件，根仓库与 CI 零改动。**

## 2. `.toolchain.json` 格式

位于模块根目录：

```json
{
  "adapter": "typescript",
  "stages": {
    "lint": "pnpm lint",
    "typecheck": "pnpm typecheck",
    "test": "pnpm test",
    "build": "pnpm build"
  }
}
```

字段说明：

- `adapter`（必填）：适配器名，对应 `tooling/adapters/<adapter>.mjs`。
- `stages`（可选）：覆盖该适配器对每个 stage 的默认命令。省略时沿用适配器默认值。
  - `build` 可省略（表示「此模块无需构建」，gate-runner 会跳过该 stage）。

## 3. 标准阶段（stage）

| stage       | 含义                                                  | 失败是否阻断 |
| ----------- | ----------------------------------------------------- | ------------ |
| `lint`      | 静态检查 / 风格                                       | 是           |
| `typecheck` | 类型检查（无类型语言可设为 no-op 或省略）             | 是           |
| `test`      | 单元 / 验收测试（须覆盖 spec 的 Acceptance Criteria） | 是           |
| `build`     | 构建产物（可省略）                                    | 是           |

## 4. gate-runner 用法

```bash
node tooling/gate-runner.mjs                              # 跑全部模块的 lint/typecheck/test/build
node tooling/gate-runner.mjs --stages lint,test          # 只跑指定阶段
node tooling/gate-runner.mjs --no-bail                   # 不遇错即停（跑完所有模块）
node tooling/gate-runner.mjs --modules logging-framework/web/Observability   # 仅指定模块
```

退出码：全部通过为 `0`；任一模块任一阶段失败为 `1`（默认 `--bail`）。

## 5. 写一个新语言适配器

新增 `tooling/adapters/<lang>.mjs`，默认导出：

```js
export default {
  name: "python",
  stages: {
    lint: "ruff check .",
    typecheck: "mypy .",
    test: "pytest",
    // build 省略 = 该语言模块默认无构建阶段
  },
};
```

无需改动 gate-runner、CI 或任何其它文件。这就是「语言无关」的落点：语言知识全部收口在 `adapters/` 一个文件里。
