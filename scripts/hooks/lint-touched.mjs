#!/usr/bin/env node
// Agent Hook（Claude Code 参考实现）：PostToolUse on Edit|Write|MultiEdit
// 强制约束：Agent 每改完一个代码文件，立刻跑 ESLint（含 @typescript-eslint/no-console 等强制规则）。
// 若发现错误，把错误暴露给 Agent 并阻断该步，迫使它当场自纠——
// 把 AGENTS.md「禁止 console.log 做生产日志」「优先复用已有模式」从口号变成写码时的实时门禁。
//
// ESLint 未安装（如尚未 pnpm install）时优雅跳过，不阻断。

import { readFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

function main() {
  let payload;
  try {
    payload = JSON.parse(readFileSync(0, 'utf8'));
  } catch {
    process.exit(0);
  }

  const tool = payload?.tool_name;
  if (!['Edit', 'Write', 'MultiEdit'].includes(tool)) process.exit(0);

  const filePath = payload?.tool_input?.file_path;
  if (!filePath || !/\.(ts|tsx|js|jsx|mjs|cjs)$/.test(filePath)) process.exit(0);

  let stdout = '';
  let stderr = '';
  try {
    const out = execFileSync('pnpm', ['exec', 'eslint', filePath], { stdio: 'pipe' });
    stdout = out.toString();
  } catch (e) {
    if (e.code === 'ENOENT') {
      // pnpm/eslint 未安装，跳过
      process.exit(0);
    }
    stdout = (e.stdout?.toString?.() || '').trim();
    stderr = (e.stderr?.toString?.() || '').trim();
  }

  const report = [stdout, stderr].filter(Boolean).join('\n');
  if (report) {
    process.stderr.write(`🔧 ESLint 发现问题（请修复后继续）：\n${report}\n`);
    process.exit(2);
  }

  process.exit(0);
}

main();
