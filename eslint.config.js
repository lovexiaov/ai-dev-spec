// ESLint 扁平配置（ESLint 9+）
// 本配置是「约束 AI 行为」的机器强制层之一：
// 把 AGENTS.md 里的口头规则（如「禁止 console.log 做生产日志」）变成 ESLint error，
// 由 Git Hooks 的 lint-staged 与 Agent 的 PostToolUse 钩子在提交前/写码后强制拦截。
import js from "@eslint/js";
import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";
import globals from "globals";

export default [
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/build/**",
      "**/coverage/**",
      "**/*.config.js",
      "**/*.config.ts",
    ],
  },
  {
    files: ["**/*.{ts,tsx,js,jsx,mjs,cjs}"],
    languageOptions: {
      parser: tsparser,
      sourceType: "module",
      ecmaVersion: 2022,
      globals: { ...globals.node, ...globals.browser },
    },
    plugins: { "@typescript-eslint": tseslint },
    rules: {
      // —— 把软规则变成硬错误 ——
      // 注意：no-console 是 ESLint 核心规则，不可加 @typescript-eslint/ 前缀。
      "no-console": [
        "error",
        { allow: ["warn", "error"] }, // 仅允许 console.warn/error 作为兜底；生产日志必须走 @scaffold/observability
      ],
      "no-debugger": "error",
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      eqeqeq: ["error", "always"],
      "no-duplicate-imports": "error",
    },
  },
];
