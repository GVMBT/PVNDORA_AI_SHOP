/**
 * Centralized Logging Utility
 *
 * Provides consistent logging across the application with:
 * - Environment-aware logging (dev/prod)
 * - Log levels (debug, info, warn, error)
 * - Optional error reporting integration
 */

type LogLevel = "debug" | "info" | "warn" | "error";

interface LoggerConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableRemoteLogging?: boolean;
  remoteEndpoint?: string;
}

class Logger {
  private config: LoggerConfig;
  private logLevels: Record<LogLevel, number> = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
  };

  constructor() {
    const isDev = import.meta.env.DEV;
    const isProd = import.meta.env.PROD;

    this.config = {
      level: isDev ? "debug" : "warn",
      enableConsole: isDev || isProd, // Always enable in both modes
      enableRemoteLogging: isProd, // Only in production
      remoteEndpoint: undefined, // Can be configured later for Sentry/etc
    };
  }

  private shouldLog(level: LogLevel): boolean {
    return this.logLevels[level] >= this.logLevels[this.config.level];
  }

  private formatMessage(level: LogLevel, message: string, ..._args: unknown[]): string {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
    return `${prefix} ${message}`;
  }

  private log(level: LogLevel, message: string, ...args: unknown[]): void {
    if (!this.shouldLog(level)) return;

    const formattedMessage = this.formatMessage(level, message, ...args);

    if (this.config.enableConsole) {
      switch (level) {
        case "debug":
          console.debug(formattedMessage, ...args);
          break;
        case "info":
          console.info(formattedMessage, ...args);
          break;
        case "warn":
          console.warn(formattedMessage, ...args);
          break;
        case "error":
          console.error(formattedMessage, ...args);
          break;
      }
    }

    // Remote logging (e.g., Sentry) can be added here
    if (this.config.enableRemoteLogging && level === "error" && this.config.remoteEndpoint) {
      this.sendToRemote(level, message, args);
    }
  }

  private sendToRemote(_level: LogLevel, _message: string, _args: unknown[]): void {
    // Placeholder for remote logging (Sentry, LogRocket, etc.)
    // Example:
    // if (window.Sentry) {
    //   window.Sentry.captureMessage(message, {
    //     level: level as Sentry.SeverityLevel,
    //     extra: args,
    //   });
    // }
  }

  debug(message: string, ...args: unknown[]): void {
    this.log("debug", message, ...args);
  }

  info(message: string, ...args: unknown[]): void {
    this.log("info", message, ...args);
  }

  warn(message: string, ...args: unknown[]): void {
    this.log("warn", message, ...args);
  }

  error(message: string, error?: Error | unknown, ...args: unknown[]): void {
    if (error instanceof Error) {
      this.log("error", message, error, error.stack, ...args);
    } else {
      this.log("error", message, error, ...args);
    }
  }

  /**
   * Log API errors with context
   */
  apiError(endpoint: string, status: number, message: string, error?: unknown): void {
    this.error(`API Error [${endpoint}]`, {
      endpoint,
      status,
      message,
      error,
    });
  }

  /**
   * Log component errors
   */
  componentError(componentName: string, error: Error, errorInfo?: React.ErrorInfo): void {
    this.error(`Component Error [${componentName}]`, error, errorInfo);
  }

  /**
   * Configure logger (e.g., for testing or custom setup)
   */
  configure(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }
}

// Export singleton instance
export const logger = new Logger();

// Export types
export type { LogLevel, LoggerConfig };
