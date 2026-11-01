/** 统一日志字段类型：前后端共用一套 schema，保证可观测数据可被聚合分析 */

export type LogLevelName = 'debug' | 'info' | 'warn' | 'error';

export interface LogContext {
  userId?: string;
  sessionId?: string;
  traceId?: string;
  [key: string]: unknown;
}

export interface LogEvent {
  timestamp: string;
  level: LogLevelName;
  message: string;
  service: string;
  env: string;
  /** 语义化事件名，如 ai_request_initiated / http_request / db_query */
  event?: string;
  userId?: string;
  sessionId?: string;
  traceId?: string;
  /** 事件专属上下文（已脱敏） */
  [key: string]: unknown;
}

export type LogSink = (line: string) => void;

export interface LoggerOptions {
  service: string;
  env: string;
  level?: LogLevelName;
  format?: 'json' | 'pretty';
  /** 脱敏字段点分路径，如 'password'、'user.email' */
  redactPaths?: string[];
  /** 自定义输出（默认 stdout；浏览器可传 fetch 上报） */
  sink?: LogSink;
}
