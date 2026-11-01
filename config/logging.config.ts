/**
 * 日志与可观测配置（要点 2 落点）
 * 集中管理：日志级别、脱敏字段、sink（stdout / Sentry / 远端）、浏览器端采样。
 * 任何新项目复制本文件即可，避免「上线才崩、查无日志」。
 */

export interface LoggingConfig {
  /** 生产用 json，开发用 pretty（可读文本） */
  format: 'json' | 'pretty';
  /** 最低输出级别 */
  level: 'debug' | 'info' | 'warn' | 'error';
  /** 服务名，写入每条日志的 service 字段 */
  service: string;
  /** 当前环境 */
  env: string;
  /**
   * 脱敏字段路径（点分）。logger 层拦截，绝不依赖调用方自觉。
   * 例：'password'、'authorization'、'user.email'
   */
  redactPaths: string[];
  /** 是否上报到 Sentry（需注入 DSN） */
  sentry: {
    enabled: boolean;
    dsn?: string;
    /** 部署时上传 source map，否则堆栈不可读 */
    uploadSourceMaps: boolean;
  };
  /** 浏览器端是否采样上报（避免淹没有效日志） */
  browser: {
    enabled: boolean;
    sampleRate: number; // 0~1
    endpoint?: string;   // 结构化日志上报地址
  };
}

export const loggingConfig: LoggingConfig = {
  format: process.env.NODE_ENV === 'production' ? 'json' : 'pretty',
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  service: process.env.SERVICE_NAME ?? 'ai-dev-spec',
  env: process.env.NODE_ENV ?? 'development',
  redactPaths: [
    'password',
    'token',
    'authorization',
    'secret',
    'apiKey',
    'user.email',
    'user.phone',
  ],
  sentry: {
    enabled: !!process.env.SENTRY_DSN,
    dsn: process.env.SENTRY_DSN,
    uploadSourceMaps: process.env.NODE_ENV === 'production',
  },
  browser: {
    enabled: true,
    sampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1,
    endpoint: process.env.LOG_ENDPOINT,
  },
};
