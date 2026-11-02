import type {
  LogContext,
  LogEvent,
  LogLevelName,
  LoggerOptions,
  LogSink,
} from "./types.js";

/** 重新导出类型，便于调用方从 logger 直接取用（如 frontend 的 createBrowserLogger）。 */
export type { LoggerOptions } from "./types.js";

const LEVEL_WEIGHT: Record<LogLevelName, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/** 深拷贝并就地脱敏：按点分路径把敏感字段替换成 [REDACTED] */
function redact(value: unknown, paths: string[], prefix = ""): unknown {
  if (value === null || typeof value !== "object") return value;
  // 数组与对象分别复制，保持原结构；用 Record 视图统一做键遍历与写回。
  const out: Record<string, unknown> | unknown[] = Array.isArray(value)
    ? [...(value as unknown[])]
    : { ...(value as Record<string, unknown>) };
  const view = out as unknown as Record<string, unknown>;
  for (const key of Object.keys(view)) {
    const full = prefix ? `${prefix}.${key}` : key;
    if (paths.includes(full)) {
      view[key] = "[REDACTED]";
    } else if (typeof view[key] === "object" && view[key] !== null) {
      view[key] = redact(view[key], paths, full);
    }
  }
  return out;
}

const defaultSink: LogSink = (line) => {
  // 错误级别走 stderr，便于容器/平台分流采集；
  // 直接用 stdout/stderr 写入，避免引入 console（生产日志须由本框架统一管控）
  if (line.includes('"level":"error"')) process.stderr.write(line + "\n");
  else process.stdout.write(line + "\n");
};

export class Logger {
  private readonly opts: Required<LoggerOptions>;
  private readonly bound: LogContext;

  constructor(options: LoggerOptions, bound: LogContext = {}) {
    this.opts = {
      level: options.level ?? "info",
      format: options.format ?? "json",
      redactPaths: options.redactPaths ?? [],
      sink: options.sink ?? defaultSink,
      service: options.service,
      env: options.env,
    };
    this.bound = bound;
  }

  /** 绑定上下文（典型：traceId / userId），返回新实例，不污染原实例 */
  child(ctx: LogContext): Logger {
    return new Logger(this.opts, { ...this.bound, ...ctx });
  }

  private emit(
    level: LogLevelName,
    message: string,
    event: string | undefined,
    extra: LogContext,
  ) {
    if (LEVEL_WEIGHT[level] < LEVEL_WEIGHT[this.opts.level]) return;
    const merged: LogEvent = {
      timestamp: new Date().toISOString(),
      level,
      message,
      service: this.opts.service,
      env: this.opts.env,
      ...this.bound,
      ...extra,
      ...(event ? { event } : {}),
    };
    const clean = redact(merged, this.opts.redactPaths) as LogEvent;
    const line =
      this.opts.format === "pretty"
        ? `${clean.timestamp} ${level.toUpperCase()} [${clean.service}] ${message} ${JSON.stringify(clean)}`
        : JSON.stringify(clean);
    this.opts.sink(line);
  }

  debug(message: string, extra: LogContext = {}, event?: string) {
    this.emit("debug", message, event, extra);
  }
  info(message: string, extra: LogContext = {}, event?: string) {
    this.emit("info", message, event, extra);
  }
  warn(message: string, extra: LogContext = {}, event?: string) {
    this.emit("warn", message, event, extra);
  }
  error(message: string, extra: LogContext = {}, event?: string) {
    this.emit("error", message, event, extra);
  }
}

/** 工厂函数：项目入口处用 config/logging.config.ts 注入即可 */
export function createLogger(options: LoggerOptions): Logger {
  return new Logger(options);
}
