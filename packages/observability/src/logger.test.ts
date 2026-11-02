import { describe, it, expect } from "vitest";
import { createLogger } from "./logger.js";
import {
  generateTraceId,
  runWithTrace,
  outgoingHeaders,
  traceIdFromHeaders,
} from "./trace.js";
import { record, snapshot } from "./metrics.js";

function parse(line: string | undefined): Record<string, unknown> {
  return JSON.parse(line ?? "{}") as Record<string, unknown>;
}

describe("Logger", () => {
  it("输出单行 JSON 且携带 service / message / extra", () => {
    const lines: string[] = [];
    const logger = createLogger({
      service: "test",
      level: "info",
      sink: (l) => lines.push(l),
    });
    logger.info("hello", { userId: "u1" });

    expect(lines).toHaveLength(1);
    const evt = parse(lines[0]);
    expect(evt.message).toBe("hello");
    expect(evt.service).toBe("test");
    expect(evt.userId).toBe("u1");
    expect(typeof evt.timestamp).toBe("string");
  });

  it("低于 minLevel 的日志被丢弃", () => {
    const lines: string[] = [];
    const logger = createLogger({
      service: "t",
      level: "warn",
      sink: (l) => lines.push(l),
    });
    logger.debug("dropped");
    expect(lines).toHaveLength(0);
    logger.error("kept");
    expect(lines).toHaveLength(1);
  });

  it("按点分路径脱敏（含嵌套对象）", () => {
    const lines: string[] = [];
    const logger = createLogger({
      service: "t",
      level: "debug",
      redactPaths: ["password", "nested.token"],
      sink: (l) => lines.push(l),
    });
    logger.info("x", { password: "secret", nested: { token: "abc", ok: 1 } });

    const evt = parse(lines[0]);
    expect(evt.password).toBe("[REDACTED]");
    const nested = evt.nested as Record<string, unknown>;
    expect(nested.token).toBe("[REDACTED]");
    expect(nested.ok).toBe(1);
  });
});

describe("trace", () => {
  it("generateTraceId 生成非空 id", () => {
    expect(generateTraceId()).toBeTruthy();
  });

  it("runWithTrace 在回调内提供上下文", () => {
    const id = generateTraceId();
    runWithTrace(id, () => {
      expect(traceIdFromHeaders({ "x-request-id": id })).toBe(id);
    });
  });

  it("outgoingHeaders 注入 x-request-id 与 traceparent", () => {
    const h = outgoingHeaders({ a: "1" });
    expect(h.a).toBe("1");
    const rid = h["x-request-id"] ?? "";
    expect(rid).toBeTruthy();
    expect(h.traceparent).toContain(rid);
  });
});

describe("metrics", () => {
  it("record + snapshot 产出 RED 指标", () => {
    record("/health", 10);
    record("/health", 20, true);
    const s = snapshot();
    const m = s["/health"];
    expect(m?.rate).toBe(2);
    expect(m?.errors).toBe(1);
    expect(m?.p50).toBeGreaterThan(0);
  });
});
