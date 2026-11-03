// tooling/adapters/typescript.mjs
// TypeScript / Node (pnpm workspace) 适配器。
// 命令在模块根目录执行，复用根 package.json 的 pnpm 脚本，
// 因此会连带触发 workspace 成员（含 Web 日志子模块）的门禁。
export default {
  name: "typescript",
  stages: {
    lint: "pnpm lint",
    typecheck: "pnpm typecheck",
    test: "pnpm test",
    build: "pnpm build",
  },
};
