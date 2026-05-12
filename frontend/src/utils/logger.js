/**
 * 统一日志工具
 * 开发环境输出所有日志，生产环境只输出错误日志
 */

const isDevelopment = process.env.NODE_ENV === 'development';

const logger = {
  /**
   * 普通日志 - 仅开发环境
   */
  log: (...args) => {
    if (isDevelopment) {
      console.log(...args);
    }
  },

  /**
   * 错误日志 - 始终记录，未来可集成错误监控服务
   */
  error: (...args) => {
    console.error(...args);
  },

  /**
   * 警告日志 - 仅开发环境
   */
  warn: (...args) => {
    if (isDevelopment) {
      console.warn(...args);
    }
  },

  /**
   * 信息日志 - 仅开发环境
   */
  info: (...args) => {
    if (isDevelopment) {
      console.info(...args);
    }
  },

  /**
   * 调试日志 - 仅开发环境
   */
  debug: (...args) => {
    if (isDevelopment) {
      console.debug(...args);
    }
  },

  /**
   * 表格日志 - 仅开发环境
   */
  table: (...args) => {
    if (isDevelopment) {
      console.table(...args);
    }
  },
};

export default logger;
