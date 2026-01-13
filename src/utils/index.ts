/**
 * Utilities Barrel Export
 *
 * Centralized exports for all utility functions.
 * Improves tree-shaking and provides consistent imports.
 */

// API Client
export { apiDelete, apiGet, apiPatch, apiPost, apiPut, apiRequest } from "./apiClient";

// API Error Handling
export {
  type ApiError,
  formatErrorForUser,
  getRetryDelay,
  isRetryableError,
  parseApiError,
} from "./apiErrorHandler";

// API Headers
export { type ApiHeaders, getApiHeaders } from "./apiHeaders";

// Authentication
export {
  getSessionToken,
  persistSessionTokenFromQuery,
  removeSessionToken,
  type SessionVerificationResult,
  saveSessionToken,
  verifySessionToken,
} from "./auth";

// Cart Converter
export {
  convertCartDataToLegacyCart,
  getCartSubtotal,
  getCartTotal,
  type LegacyCart,
  type LegacyCartItem,
} from "./cartConverter";

// Currency
export { type CurrencyCode, formatPrice, getCurrencySymbol } from "./currency";

// Date Formatting
export { formatDate, formatDateISO, formatDateTime, formatRelativeTime } from "./date";

// ID Generation
export { generateHashId, generateId, generateShortId } from "./id";

// Logging
export { type LoggerConfig, type LogLevel, logger } from "./logger";

// Number Formatting
export {
  clamp,
  formatBytes,
  formatCompactNumber,
  formatNumber,
  formatPercentage,
  formatPercentageWithSign,
  isInRange,
  roundTo,
} from "./number";

// Storage
export { localStorage, sessionStorage } from "./storage";

// Telegram WebApp
export {
  expandWebApp,
  getStartParam,
  getTelegramInitData,
  getTelegramUser,
  getTelegramWebApp,
  isTelegramWebApp,
  readyWebApp,
  requestFullscreen,
} from "./telegram";
