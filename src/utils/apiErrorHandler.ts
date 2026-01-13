/**
 * Centralized API Error Handler
 *
 * Provides consistent error handling and user-friendly error messages
 * for API requests across the application.
 */

import { logger } from "./logger";

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
  retryable?: boolean;
}

/**
 * Parse error from API response
 */
export function parseApiError(error: unknown, endpoint?: string): ApiError {
  if (error instanceof Error) {
    // Check for HTTP status codes in message
    const statusMatch = error.message.match(/HTTP (\d+)/);
    const status = statusMatch ? parseInt(statusMatch[1], 10) : undefined;

    // Determine if error is retryable
    const retryable = status ? [429, 502, 503, 504].includes(status) : false;

    // Extract user-friendly message
    let message = error.message;

    // Remove technical prefixes
    message = message.replace(/^CrystalPay API error:\s*/i, "");

    // Handle specific status codes
    if (status === 429) {
      message = message || "Слишком много запросов. Подождите минуту и попробуйте снова.";
    } else if (status === 502 || status === 503) {
      message = message || "Платёжная система временно недоступна. Попробуйте позже.";
    } else if (status === 401) {
      message = "Сессия истекла. Пожалуйста, войдите снова.";
    } else if (status === 403) {
      message = "Доступ запрещён. У вас нет прав для выполнения этого действия.";
    } else if (status === 404) {
      message = "Ресурс не найден.";
    } else if (status === 500) {
      message = "Внутренняя ошибка сервера. Попробуйте позже.";
    }

    logger.apiError(endpoint || "unknown", status || 0, message, error);

    return {
      message,
      status,
      retryable,
    };
  }

  // Fallback for unknown error types
  const message = "Произошла неизвестная ошибка. Попробуйте позже.";
  logger.error("Unknown API error format", error);

  return {
    message,
    retryable: false,
  };
}

/**
 * Check if error is retryable
 */
export function isRetryableError(error: ApiError): boolean {
  return error.retryable === true;
}

/**
 * Get retry delay in milliseconds based on error
 */
export function getRetryDelay(error: ApiError, attempt: number): number {
  if (!isRetryableError(error)) return 0;

  // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
  const baseDelay = 1000;
  const maxDelay = 30000;
  const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);

  // Add jitter (±20%)
  const jitter = delay * 0.2 * (Math.random() * 2 - 1);
  return Math.max(0, delay + jitter);
}

/**
 * Format error for user display
 */
export function formatErrorForUser(error: ApiError): string {
  return error.message;
}
