/**
 * 日志与可观测配置（要点 2 落点）
 * 集中管理：日志级别、脱敏字段、sink（stdout / Sentry / 远端）、浏览器端采样。
 *
 * 语言中立的规范配置见同目录 logging.config.json（Schema：logging.config.schema.json）。
 * 本文件是「TypeScript 适配器」示例：直接读取并复用那份中立 JSON，
 * 保证换语言不改配置（见 docs/logging-framework/INTERFACE.md §4）。
 */

import loggingConfigJson from "./logging.config.json" with { type: "json" };

export interface LoggingConfig {
  /** 生产用 json，开发用 pretty（可读文本） */
  format: "json" | "pretty";
  /** 最低输出级别（与 Schema v1 词表一致：trace/debug/info/warn/error/critical） */
  level: "trace" | "debug" | "info" | "warn" | "error" | "critical";
  /** 服务名，写入每条日志的 service 字段 */
  service: string;
  /** 当前环境 */
  env: string;
  /** 发布标识（可选）：semver / git sha / build number，写入每条日志的 release 字段 */
  release?: string;
  /**
   * 脱敏字段路径（点分）。logger 层拦截，绝不依赖调用方自觉。
   * 例：'password'、'authorization'、'user.email'
   */
  redactPaths: string[];
  /** 是否上报到 Sentry（需注入 DSN） */
  sentry: {
    enabled: boolean;
    dsn?: string;
  };
  /** 浏览器端是否采样上报（避免淹没有效日志） */
  browser: {
    enabled: boolean;
    sampleRate: number; // 0~1
    endpoint?: string; // 结构化日志上报地址
  };
}

export const loggingConfig: LoggingConfig =
  loggingConfigJson as unknown as LoggingConfig;
