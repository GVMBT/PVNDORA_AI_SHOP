/**
 * Error Handler Hook
 * 
 * Centralized error handling with consistent logging and user feedback.
 */

import { useCallback } from 'react';
import { logger } from '../utils/logger';
import { useTelegram } from './useTelegram';

export interface ErrorContext {
  component?: string;
  action?: string;
  endpoint?: string;
  userId?: string | number;
  [key: string]: unknown;
}

export interface ErrorHandlerOptions {
  /** Show alert to user */
  showAlert?: boolean;
  /** Log error to console/remote */
  logError?: boolean;
  /** Custom error message for user */
  userMessage?: string;
  /** Additional context */
  context?: ErrorContext;
  /** Fallback action on error */
  onError?: (error: Error) => void;
}

/**
 * Hook for centralized error handling
 */
export function useErrorHandler() {
  const { showAlert } = useTelegram();

  /**
   * Handle error with consistent logging and user feedback
   */
  const handleError = useCallback(
    (error: unknown, options: ErrorHandlerOptions = {}) => {
      const {
        showAlert: shouldShowAlert = true,
        logError: shouldLog = true,
        userMessage,
        context = {},
        onError,
      } = options;

      // Convert to Error if needed
      const err = error instanceof Error ? error : new Error(String(error));

      // Log error
      if (shouldLog) {
        const logContext = {
          message: err.message,
          stack: err.stack,
          ...context,
        };
        logger.error('Error occurred', err, logContext);
      }

      // Show user-friendly message
      if (shouldShowAlert) {
        const message = userMessage || getErrorMessage(err, context);
        showAlert(message).catch(() => {
          // Fallback to window.alert if Telegram alert fails
          window.alert(message);
        });
      }

      // Call custom handler if provided
      if (onError) {
        onError(err);
      }

      return err;
    },
    [showAlert]
  );

  /**
   * Handle API errors specifically
   */
  const handleApiError = useCallback(
    (
      error: unknown,
      endpoint: string,
      options: Omit<ErrorHandlerOptions, 'context'> = {}
    ) => {
      return handleError(error, {
        ...options,
        context: {
          endpoint,
          action: 'api_request',
        },
        userMessage: options.userMessage || 'Произошла ошибка при запросе к серверу',
      });
    },
    [handleError]
  );

  /**
   * Handle validation errors
   */
  const handleValidationError = useCallback(
    (error: unknown, field?: string, options: Omit<ErrorHandlerOptions, 'context'> = {}) => {
      return handleError(error, {
        ...options,
        context: {
          field,
          action: 'validation',
        },
        userMessage: options.userMessage || `Ошибка валидации${field ? `: ${field}` : ''}`,
      });
    },
    [handleError]
  );

  /**
   * Handle network errors
   */
  const handleNetworkError = useCallback(
    (error: unknown, options: Omit<ErrorHandlerOptions, 'context'> = {}) => {
      return handleError(error, {
        ...options,
        context: {
          action: 'network_request',
        },
        userMessage: options.userMessage || 'Ошибка сети. Проверьте подключение к интернету.',
      });
    },
    [handleError]
  );

  return {
    handleError,
    handleApiError,
    handleValidationError,
    handleNetworkError,
  };
}

/**
 * Get user-friendly error message from error
 */
function getErrorMessage(error: Error, context: ErrorContext): string {
  // Check for common error patterns
  if (error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
    return 'Ошибка сети. Проверьте подключение к интернету.';
  }

  if (error.message.includes('401') || error.message.includes('Unauthorized')) {
    return 'Требуется авторизация. Пожалуйста, войдите в систему.';
  }

  if (error.message.includes('403') || error.message.includes('Forbidden')) {
    return 'Доступ запрещен.';
  }

  if (error.message.includes('404') || error.message.includes('Not Found')) {
    return 'Ресурс не найден.';
  }

  if (error.message.includes('429') || error.message.includes('Too Many Requests')) {
    return 'Слишком много запросов. Подождите минуту и попробуйте снова.';
  }

  if (error.message.includes('500') || error.message.includes('Internal Server Error')) {
    return 'Ошибка сервера. Попробуйте позже.';
  }

  if (error.message.includes('503') || error.message.includes('Service Unavailable')) {
    return 'Сервис временно недоступен. Попробуйте позже.';
  }

  // Component-specific messages
  if (context.component) {
    return `Ошибка в ${context.component}: ${error.message}`;
  }

  // Generic message
  return error.message || 'Произошла неизвестная ошибка';
}

export default useErrorHandler;





