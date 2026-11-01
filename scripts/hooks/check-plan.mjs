#!/usr/bin/env node
// Agent Hook（Claude Code 参考实现）：PreToolUse on Edit|Write|MultiEdit
// 强制约束：修改 src/ 业务代码前，必须存在至少一个已「✅ 人工批准」的 plan.md。
// 对应 AGENTS.md §3 NEVER「plan.md 未含 ✅ Human Approval 标记前，修改 src/ 业务代码」。
//
// 这是「机器强制」而非「文档建议」：Agent 在改动 src/ 前会被直接拦截并看到原因，
// 无法靠「假装读过 AGENTS.md」绕过。紧急绕过（需人工知晓）：SKIP_PLAN_CHECK=1。

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const SKIP = process.env.SKIP_PLAN_CHECK === '1';

function hasApprovedPlan() {
  const specsDir = join(process.cwd(), 'docs', 'specs');
  if (!existsSync(specsDir)) return false;
  let entries;
  try {
    entries = readdirSync(specsDir).filter((e) => e !== '_template');
  } catch {
    return false;
  }
  for (const feature of entries) {
    const plan = join(specsDir, feature, 'plan.md');
    if (!existsSync(plan)) continue;
    let text;
    try {
      text = readFileSync(plan, 'utf8');
    } catch {
      continue;
    }
    const idx = text.indexOf('Human Approval');
    if (idx === -1) continue;
    // 只看 Human Approval 区块之后的内容，避免误判模板里的示例勾选
    const tail = text.slice(idx, idx + 400);
    if (/✅|\[x\]/.test(tail)) return true;
  }
  return false;
}

function main() {
  if (SKIP) process.exit(0);

  let payload;
  try {
    payload = JSON.parse(readFileSync(0, 'utf8'));
  } catch {
    process.exit(0);
  }

  const tool = payload?.tool_name;
  if (!['Edit', 'Write', 'MultiEdit'].includes(tool)) process.exit(0);

  const filePath = payload?.tool_input?.file_path;
  if (!filePath) process.exit(0);

  const isSrcEdit = /(^|\/)src\//.test(filePath) || /^src\//.test(filePath);
  if (!isSrcEdit) process.exit(0);

  if (hasApprovedPlan()) process.exit(0);

  process.stderr.write(
    [
      '🚫 约束拦截：修改 src/ 业务代码前，必须先有已人工批准的 plan.md。',
      '   步骤：docs/specs/<feature>/spec.md → plan.md → 人在「✅ Human Approval」区块批准（勾选 - [x] 或写 ✅）→ 再改 src/。',
      '   紧急绕过（会记入日志，慎用）：SKIP_PLAN_CHECK=1',
    ].join('\n') + '\n',
  );
  process.exit(2);
}

main();
