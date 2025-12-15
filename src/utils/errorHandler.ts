/**
 * Error Handler Utilities
 * 
 * Provides utilities for consistent error handling across the application.
 */

import { logger } from './logger';

/**
 * Extract error message from unknown error type
 */
export function getErrorMessage(error: unknown, fallback = 'An error occurred'): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object' && 'message' in error) {
    return String(error.message);
  }
  return fallback;
}

/**
 * Check if error is a specific HTTP status code
 */
export function isHttpError(error: unknown, statusCode: number): boolean {
  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    return message.includes(`http ${statusCode}`) || message.includes(`${statusCode}`);
  }
  return false;
}

/**
 * Check if error indicates network failure
 */
export function isNetworkError(error: unknown): boolean {
  const message = getErrorMessage(error).toLowerCase();
  return (
    message.includes('network') ||
    message.includes('fetch') ||
    message.includes('connection') ||
    message.includes('timeout') ||
    message.includes('failed to fetch')
  );
}

/**
 * Get user-friendly error message
 */
export function getUserFriendlyError(error: unknown): string {
  const message = getErrorMessage(error);
  
  // Network errors
  if (isNetworkError(error)) {
    return 'Network error. Please check your connection and try again.';
  }
  
  // HTTP 404
  if (isHttpError(error, 404)) {
    return 'Resource not found.';
  }
  
  // HTTP 429 (Rate limiting)
  if (isHttpError(error, 429)) {
    return 'Too many requests. Please wait a moment and try again.';
  }
  
  // HTTP 500-503 (Server errors)
  if (isHttpError(error, 500) || isHttpError(error, 502) || isHttpError(error, 503)) {
    return 'Server error. Please try again later.';
  }
  
  // Filter out technical details from error messages
  const technicalPatterns = [
    /^error:/i,
    /^exception:/i,
    /at .+\.\w+ \(.+\)/,
    /\[object \w+\]/,
    /undefined|null/,
  ];
  
  let cleanMessage = message;
  for (const pattern of technicalPatterns) {
    cleanMessage = cleanMessage.replace(pattern, '');
  }
  
  cleanMessage = cleanMessage.trim();
  
  // Return original message if cleaned message is meaningful
  if (cleanMessage.length > 10 && cleanMessage.length < 200) {
    return cleanMessage;
  }
  
  // Default fallback
  return 'An unexpected error occurred. Please try again.';
}

/**
 * Log error with context
 */
export function logError(error: unknown, context?: Record<string, unknown>): void {
  const errorMessage = getErrorMessage(error);
  const errorInstance = error instanceof Error ? error : new Error(errorMessage);
  
  logger.error('Error occurred', errorInstance, context);
}

/**
 * Handle error and return user-friendly message
 * Logs error automatically
 */
export function handleError(error: unknown, context?: Record<string, unknown>): string {
  logError(error, context);
  return getUserFriendlyError(error);
}







