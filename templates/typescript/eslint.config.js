import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";

// 扁平配置（ESLint 9）。仅声明强制规则，不依赖 @eslint/js。
// 关键：no-console 是核心规则（不是 @typescript-eslint 前缀），写错前缀会让整份配置静默失效。
export default [
  {
    files: ["**/*.ts", "**/*.mjs"],
    languageOptions: {
      parser: tsparser,
      ecmaVersion: 2022,
      sourceType: "module",
    },
    plugins: {
      "@typescript-eslint": tseslint,
    },
    rules: {
      "no-console": "error",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_" },
      ],
    },
  },
  {
    ignores: ["dist/**", "node_modules/**", "tooling/**"],
  },
];
