// tooling/lib/scaffold.mjs
// 供 init.mjs / add-to-existing.mjs 复用的共享 helper。
// 只做「文件搬运 + 配置生成」，不认识任何语言工具。
import {
  cpSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  writeFileSync,
  chmodSync,
  statSync,
} from "node:fs";
import { join, dirname, resolve, basename, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const SCAFFOLD_ROOT = resolve(__dirname, "..", "..");
export const TEMPLATES_DIR = join(SCAFFOLD_ROOT, "templates");
export const TOOLING_DIR = join(SCAFFOLD_ROOT, "tooling");
export const SUPPORTED_LANGS = ["typescript", "swift", "python"];

// 与 tooling/adapters/*.mjs 的默认值保持一致（新增语言时同步这里）。
export const ADAPTER_STAGES = {
  typescript: {
    lint: "pnpm lint",
    typecheck: "pnpm typecheck",
    test: "pnpm test",
    build: "pnpm build",
  },
  swift: {
    lint: "swiftlint",
    typecheck: "swift build",
    test: "swift test",
    build: "swift build",
  },
  python: {
    lint: "ruff check .",
    typecheck: "mypy .",
    test: "pytest",
    // build 省略：Python 模块默认无独立构建阶段
  },
};

export function log(msg) {
  console.error(msg);
}

export function ensureDir(p) {
  mkdirSync(p, { recursive: true });
}

export function copyDir(src, dest) {
  ensureDir(dest);
  cpSync(src, dest, { recursive: true, force: true });
}

export function writeJSON(path, obj) {
  writeFileSync(path, JSON.stringify(obj, null, 2) + "\n");
}

export function writeToolchain(target, lang) {
  const tc = { adapter: lang, stages: ADAPTER_STAGES[lang] };
  writeJSON(join(target, ".toolchain.json"), tc);
  return tc;
}

export function deriveProjectName(target) {
  const base = basename(resolve(target));
  return (
    base
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "app"
  );
}

export function toPascalCase(name) {
  return name
    .split(/[^a-zA-Z0-9]+/)
    .filter(Boolean)
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join("");
}

// 把目录下（排除 .git/node_modules/tooling）所有文件中的 {{TOKEN}} 替换为 value。
export function replacePlaceholder(root, token, value) {
  const skip = new Set([".git", "node_modules", "tooling", ".husky"]);
  function walk(dir) {
    let entries;
    try {
      entries = readdirSync(dir);
    } catch {
      return;
    }
    for (const name of entries) {
      if (skip.has(name)) continue;
      const full = join(dir, name);
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) walk(full);
      else {
        try {
          const text = readFileSync(full, "utf8");
          if (text.includes(token)) {
            writeFileSync(full, text.split(token).join(value));
          }
        } catch {
          /* 非文本文件忽略 */
        }
      }
    }
  }
  walk(root);
}

// 安装门禁 hook：TS 走 husky（.husky/ + package.json prepare），其它走 git 原生 hooks。
export function installGitHooks(target, lang) {
  const hooksSrc = join(TOOLING_DIR, "hooks");
  const names = ["pre-commit", "pre-push", "commit-msg"];
  if (lang === "typescript") {
    const huskyDir = join(target, ".husky");
    ensureDir(huskyDir);
    for (const h of names) {
      cpSync(join(hooksSrc, h), join(huskyDir, h), { force: true });
      chmodSync(join(huskyDir, h), 0o755);
    }
    log("  · hooks 写入 .husky/（由 package.json 的 prepare: husky 激活）");
  } else {
    const gitHooks = join(target, ".git", "hooks");
    if (!existsSync(gitHooks)) {
      log("  · 跳过 git hooks：未找到 .git/hooks（请先 git init）");
      return;
    }
    for (const h of names) {
      cpSync(join(hooksSrc, h), join(gitHooks, h), { force: true });
      chmodSync(join(gitHooks, h), 0o755);
    }
    log("  · hooks 写入 .git/hooks/（git 原生，无需 husky）");
  }
}

export function isEmptyDir(p) {
  if (!existsSync(p)) return true;
  let entries;
  try {
    entries = readdirSync(p);
  } catch {
    return false;
  }
  return entries.length === 0;
}

export { relative };
