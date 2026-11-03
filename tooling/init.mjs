#!/usr/bin/env node
// tooling/init.mjs — 模式一：生成一个新的语言中立项目。
// 用法: node tooling/init.mjs <lang> <target-dir> [--force] [--install] [--dry-run]
//   lang: typescript | swift | python
//   --force     覆盖目标目录中已存在的内容
//   --install   生成后运行包管理器安装依赖（仅 typescript 走 pnpm）
//   --dry-run   只打印将执行的操作，不写任何文件
import { existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";
import {
  TEMPLATES_DIR,
  TOOLING_DIR,
  SUPPORTED_LANGS,
  copyDir,
  writeToolchain,
  deriveProjectName,
  toPascalCase,
  replacePlaceholder,
  installGitHooks,
  isEmptyDir,
  log,
} from "./lib/scaffold.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

function printHelp() {
  console.error(
    `用法: node tooling/init.mjs <lang> <target-dir> [--force] [--install] [--dry-run]
  lang: ${SUPPORTED_LANGS.join(" | ")}
  --force     覆盖目标目录中已存在的内容
  --install   生成后安装依赖（仅 typescript 执行 pnpm install）
  --dry-run   只打印计划，不写文件`,
  );
}

function parseArgs(argv) {
  const opts = {
    lang: null,
    target: null,
    force: false,
    install: false,
    dry: false,
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--force") opts.force = true;
    else if (a === "--install") opts.install = true;
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
  const baseTpl = join(TEMPLATES_DIR, "base");
  const langTpl = join(TEMPLATES_DIR, opts.lang);

  if (!existsSync(baseTpl)) {
    console.error(`❌ 找不到模板目录：${baseTpl}`);
    process.exit(1);
  }
  if (!existsSync(langTpl)) {
    console.error(`❌ 找不到语言模板：${langTpl}`);
    process.exit(1);
  }

  if (existsSync(target) && !isEmptyDir(target) && !opts.force) {
    console.error(
      `❌ 目标目录非空：${target}\n   使用 --force 覆盖，或换一个空目录。`,
    );
    process.exit(2);
  }

  const name = deriveProjectName(target);
  const pascal = toPascalCase(name);

  const plan = [
    `复制 templates/base/        → ${target}`,
    `复制 templates/${opts.lang}/  → ${target}`,
    `复制 tooling/ 执械          → ${target}/tooling`,
    `生成 .toolchain.json        → ${target}/.toolchain.json (adapter=${opts.lang})`,
    `安装 hooks                 → ${opts.lang === "typescript" ? ".husky/" : ".git/hooks/"}`,
    `替换占位符 {{PROJECT_NAME}}  → ${name} / ${pascal}`,
  ];

  if (opts.dry) {
    log("\n[dry-run] 将执行以下操作：");
    for (const l of plan) log("  · " + l);
    log("\n（未写入任何文件）\n");
    return;
  }

  log(`\n🚀 初始化语言中立项目：${name}（${opts.lang}）`);
  copyDir(baseTpl, target);
  copyDir(langTpl, target);
  copyDir(TOOLING_DIR, join(target, "tooling"));
  writeToolchain(target, opts.lang);
  replacePlaceholder(target, "{{PROJECT_NAME}}", pascal);
  // package.json 的 name 字段用 kebab-case 更自然（模板里已是 "{{PKG_NAME}}"，token 不含引号）
  if (opts.lang === "typescript")
    replacePlaceholder(target, "{{PKG_NAME}}", name);
  installGitHooks(target, opts.lang);
  log("✅ 项目骨架已生成。");

  if (opts.install && opts.lang === "typescript") {
    log("\n📦 安装依赖（pnpm install）...");
    execSync("pnpm install", { cwd: target, stdio: "inherit" });
    log("✅ 依赖安装完成。运行 `pnpm gate` 验收门禁。");
  } else if (opts.install) {
    log(
      `\n⚠️  --install 目前仅对 typescript 自动执行；${opts.lang} 请按其生态手动安装依赖。`,
    );
  }

  log("\n下一步：");
  log(`  cd ${opts.target}`);
  if (opts.lang === "typescript") {
    log("  pnpm gate          # 跑 lint/typecheck/test/build");
    log("  pnpm install       # 若未带 --install");
  } else if (opts.lang === "swift") {
    log("  swift build && swift test");
  } else if (opts.lang === "python") {
    log("  ruff check . && mypy . && pytest");
  }
  log("  node tooling/gate-runner.mjs   # 或经中立门禁编排器");
}

main();
