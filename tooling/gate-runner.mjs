#!/usr/bin/env node
// tooling/gate-runner.mjs
// 中立门禁编排器：发现 .toolchain.json → 加载适配器 → 跑 lint/typecheck/test/build。
// 本文件**不认识任何语言工具**；语言知识全部在 tooling/adapters/<name>.mjs。
// 设计见 docs/gate-contract.md。
import { execFileSync } from "node:child_process";
import { readdirSync, statSync, readFileSync, existsSync } from "node:fs";
import { join, dirname, resolve, relative } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TOOLING_DIR = __dirname;
const ROOT = resolve(TOOLING_DIR, "..");
const ALL_STAGES = ["lint", "typecheck", "test", "build"];

function parseArgs(argv) {
  const opts = { stages: null, bail: true, modules: null };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--stages")
      opts.stages = argv[++i].split(",").map((s) => s.trim());
    else if (a === "--no-bail") opts.bail = false;
    else if (a === "--modules")
      opts.modules = argv[++i].split(",").map((s) => resolve(ROOT, s.trim()));
    else if (a === "--help" || a === "-h") {
      console.error(
        "Usage: node tooling/gate-runner.mjs [--stages lint,test] [--no-bail] [--modules <path,...>]",
      );
      process.exit(0);
    }
  }
  return opts;
}

function discoverToolchains(root, modulesFilter) {
  const found = [];
  function walk(dir) {
    let entries;
    try {
      entries = readdirSync(dir);
    } catch {
      return;
    }
    for (const name of entries) {
      if (name === "node_modules" || name === ".git") continue;
      const full = join(dir, name);
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) walk(full);
      else if (name === ".toolchain.json") found.push(full);
    }
  }
  if (modulesFilter) {
    for (const m of modulesFilter) {
      const f = join(m, ".toolchain.json");
      if (existsSync(f)) found.push(f);
    }
  } else {
    walk(root);
  }
  return found;
}

async function loadAdapter(name) {
  const p = join(TOOLING_DIR, "adapters", `${name}.mjs`);
  if (!existsSync(p)) {
    console.error(`❌ 找不到适配器 tooling/adapters/${name}.mjs`);
    process.exit(1);
  }
  const mod = await import(pathToFileURL(p).href);
  return mod.default;
}

async function main() {
  const opts = parseArgs(process.argv);
  const toolchains = discoverToolchains(ROOT, opts.modules);
  if (toolchains.length === 0) {
    console.error("⚠️  未发现任何 .toolchain.json，跳过门禁。");
    return;
  }
  const stages = opts.stages && opts.stages.length ? opts.stages : ALL_STAGES;

  let failed = 0;
  for (const tcPath of toolchains) {
    const moduleRoot = dirname(tcPath);
    const tc = JSON.parse(readFileSync(tcPath, "utf8"));
    const adapter = await loadAdapter(tc.adapter);
    const label = relative(ROOT, moduleRoot) || "(root)";
    console.error(`\n📦 模块 ${label}  [adapter=${tc.adapter}]`);

    for (const stage of stages) {
      const cmd = tc.stages?.[stage] ?? adapter.stages?.[stage];
      if (!cmd) {
        console.error(`   · ${stage}: (未声明，跳过)`);
        continue;
      }
      console.error(`   ▶ ${stage}: ${cmd}`);
      try {
        execFileSync("sh", ["-c", cmd], { cwd: moduleRoot, stdio: "inherit" });
      } catch {
        failed++;
        console.error(`   ❌ ${stage} 失败 (${label})`);
        if (opts.bail) {
          console.error(`\n门禁中断（--bail）。失败阶段：${stage} @ ${label}`);
          process.exit(1);
        }
      }
    }
  }

  if (failed > 0) {
    console.error(`\n❌ 门禁失败：${failed} 个阶段未通过。`);
    process.exit(1);
  }
  console.error("\n✅ 全部门禁通过。");
}

main();
