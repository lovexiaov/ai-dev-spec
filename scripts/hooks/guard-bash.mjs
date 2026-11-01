#!/usr/bin/env node
// Agent Hook（Claude Code 参考实现）：PreToolUse on Bash
// 强制约束：拦截高风险/不可逆命令，落实 AGENTS.md §3 NEVER 与 constitution §2.5「不可逆操作需人工确认」。
// 被拦截：rm -rf /、git push --force、git reset --hard、git clean -fdx、fork bomb、sudo、mkfs、dd、chmod 777 / 等。
// 紧急绕过（需人工知晓）：SKIP_BASH_GUARD=1。

import { readFileSync } from 'node:fs';

const SKIP = process.env.SKIP_BASH_GUARD === '1';

const DANGEROUS = [
  /rm\s+-rf?\s+\//, // rm -rf /
  /rm\s+-rf?\s+[*~]/, // rm -rf *
  /git\s+push\s+.*(--force|-f)\b/, // git push --force
  /git\s+reset\s+--hard/, // git reset --hard
  /git\s+clean\s+-[a-z]*f[a-z]*d/, // git clean -fdx
  /git\s+checkout\s+\.\s*$/m, // git checkout .
  /:\s*\(\s*\)\s*\{.*\|\s*:/, // fork bomb
  /\bsudo\s+/, // sudo
  /mkfs\./, // mkfs.*
  /dd\s+if=/, // dd if=
  /chmod\s+-R\s+777\s+\//, // chmod -R 777 /
  />\s*\/dev\/sd[a-z]/, // writing raw block device
];

function main() {
  if (SKIP) process.exit(0);

  let payload;
  try {
    payload = JSON.parse(readFileSync(0, 'utf8'));
  } catch {
    process.exit(0);
  }

  if (payload?.tool_name !== 'Bash') process.exit(0);
  const command = payload?.tool_input?.command || '';
  if (typeof command !== 'string') process.exit(0);

  for (const re of DANGEROUS) {
    if (re.test(command)) {
      process.stderr.write(
        [
          '🚫 约束拦截：检测到高风险命令，已被 Agent Hook 阻止：',
          `   ${command}`,
          '   此类操作不可逆或影响范围过大，请先人工确认。',
          '   如确需执行：SKIP_BASH_GUARD=1（并说明原因）。',
        ].join('\n') + '\n',
      );
      process.exit(2);
    }
  }

  process.exit(0);
}

main();
