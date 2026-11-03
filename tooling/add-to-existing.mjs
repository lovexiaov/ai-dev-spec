#!/usr/bin/env node
// tooling/add-to-existing.mjs — 模式二：为已有项目追加 Agent 约束 + 统一日志框架。
// 只复制「约束规范 + 配置 + 中立执械 + hook」，绝不触碰已有业务代码。
// 用法: node tooling/add-to-existing.mjs <lang> <existing-dir> [--force] [--dry-run]
import { existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  TEMPLATES_DIR,
  TOOLING_DIR,
  SUPPORTED_LANGS,
  copyDir,
  writeToolchain,
  installGitHooks,
  log,
} from "./lib/scaffold.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

function printHelp() {
  console.error(
    `用法: node tooling/add-to-existing.mjs <lang> <existing-dir> [--force] [--dry-run]
  lang: ${SUPPORTED_LANGS.join(" | ")}
  仅为已有项目追加：Agent 约束(.agent/)、中立 docs、日志配置(config/)、
  门禁执械(tooling/) 与 git hooks；不修改任何已有源文件。
  --force   覆盖已存在的同名文件（.toolchain.json / config / .agent / tooling）
  --dry-run 只打印计划，不写文件`,
  );
}

function parseArgs(argv) {
  const opts = { lang: null, target: null, force: false, dry: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--force") opts.force = true;
    else if (a === "--dry-run") opts.dry = true;
    else if (a === "-h" || a === "--help") {
      printHelp();
      process.exit(0);
    } else if (!opts.lang) opts.lang = a;
    else if (!opts.target) opts.target = a;
  }
  return opts;
}

function main() {
  const opts = parseArgs(process.argv);
  if (!opts.lang || !opts.target) {
    printHelp();
    process.exit(2);
  }
  if (!SUPPORTED_LANGS.includes(opts.lang)) {
    console.error(
      `❌ 不支持的语言：${opts.lang}（支持：${SUPPORTED_LANGS.join(", ")}）`,
    );
    process.exit(2);
  }
  const target = resolve(opts.target);
  if (!existsSync(target)) {
    console.error(`❌ 目录不存在：${target}`);
    process.exit(2);
  }

  const baseTpl = join(TEMPLATES_DIR, "base");
  const plan = [
    `复制 .agent/（Agent 约束）          → ${target}/.agent`,
    `复制 config/（中立日志配置）        → ${target}/config`,
    `复制 docs/（中立契约：spec/gate/日志接口/schema） → ${target}/docs`,
    `复制 tooling/（中立门禁执械）       → ${target}/tooling`,
    `生成 .toolchain.json                → ${target}/.toolchain.json (adapter=${opts.lang})`,
    `安装 hooks                         → ${opts.lang === "typescript" ? ".husky/" : ".git/hooks/"}`,
  ];

  if (opts.dry) {
    log("\n[dry-run] 将执行以下操作（不影响任何已有业务代码）：");
    for (const l of plan) log("  · " + l);
    log("\n（未写入任何文件）\n");
    return;
  }

  log(`\n🔌 为已有项目追加约束 + 日志框架（${opts.lang}）：${target}`);
  copyDir(join(baseTpl, ".agent"), join(target, ".agent"));
  copyDir(join(baseTpl, "config"), join(target, "config"));
  copyDir(join(baseTpl, "docs"), join(target, "docs"));
  copyDir(TOOLING_DIR, join(target, "tooling"));
  writeToolchain(target, opts.lang);
  installGitHooks(target, opts.lang);
  log("✅ 已追加。原有源码未改动。");

  log("\n下一步：");
  log("  node tooling/gate-runner.mjs        # 校验门禁可运行");
  log("  按 docs/spec-format.md 新建特性规范，并把验收条件接进 test 阶段。");
}

main();
