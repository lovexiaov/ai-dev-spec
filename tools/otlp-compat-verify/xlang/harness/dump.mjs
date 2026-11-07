// 跨语言一致性 dump（Web/TS）：读样例事件数组，写出 logs / traces 两份 OTLP/JSON。
//
// 用法：node dump.mjs <samples.json> <logs.out> <traces.out>
// 依赖：环境变量 AGENTLOG_WEB_DIST 指向 tsc 编译产物目录（含 otlp.js）。
// 说明：不直接 import .ts —— Node 的类型剥离不会把 `./ids.js` 改写回 `./ids.ts`。
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const distDir = process.env.AGENTLOG_WEB_DIST;
if (!distDir) {
  console.error("AGENTLOG_WEB_DIST 未设置");
  process.exit(2);
}

const { toOtlp, toOtlpJSON } = await import(
  pathToFileURL(resolve(distDir, "otlp.js")).href
);

const [samplesPath, logsPath, tracesPath] = process.argv.slice(2);
const samples = JSON.parse(readFileSync(samplesPath, "utf8"));
const batch = toOtlp(samples);
writeFileSync(logsPath, toOtlpJSON(batch.logs));
writeFileSync(tracesPath, toOtlpJSON(batch.traces));
// 仓库 eslint 把 no-console 设为 error（除 warn/error 外），这里用 stdout 直写
process.stdout.write("web: logs+traces written\n");
