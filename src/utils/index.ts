/**
 * Utilities Barrel Export
 * 
 * Centralized exports for all utility functions.
 * Improves tree-shaking and provides consistent imports.
 */

// API Client
export {
  apiRequest,
  apiGet,
  apiPost,
  apiPut,
  apiPatch,
  apiDelete,
} from './apiClient';

// API Error Handling
export {
  parseApiError,
  isRetryableError,
  getRetryDelay,
  formatErrorForUser,
  type ApiError,
} from './apiErrorHandler';

// API Headers
export {
  getApiHeaders,
  type ApiHeaders,
} from './apiHeaders';

// Authentication
export {
  persistSessionTokenFromQuery,
  verifySessionToken,
  getSessionToken,
  saveSessionToken,
  removeSessionToken,
  type SessionVerificationResult,
} from './auth';

// Cart Converter
export {
  convertCartDataToLegacyCart,
  getCartSubtotal,
  getCartTotal,
  type LegacyCartItem,
  type LegacyCart,
} from './cartConverter';

// Currency
export {
  getCurrencySymbol,
  formatPrice,
  type CurrencyCode,
} from './currency';

// Date Formatting
export {
  formatRelativeTime,
  formatDate,
  formatDateISO,
  formatDateTime,
} from './date';

// ID Generation
export {
  generateId,
  generateShortId,
  generateHashId,
} from './id';

// Logging
export {
  logger,
  type LogLevel,
  type LoggerConfig,
} from './logger';

// Number Formatting
export {
  formatCompactNumber,
  formatNumber,
  formatPercentage,
  formatPercentageWithSign,
  formatBytes,
  clamp,
  roundTo,
  isInRange,
} from './number';

// Storage
export {
  sessionStorage,
  localStorage,
} from './storage';

// Telegram WebApp
export {
  getTelegramWebApp,
  getTelegramInitData,
  getTelegramUser,
  isTelegramWebApp,
  getStartParam,
  requestFullscreen,
  expandWebApp,
  readyWebApp,
} from './telegram';

















