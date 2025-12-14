/**
 * PVNDORA Application Configuration
 * 
 * Centralized configuration for all app settings.
 * Environment variables are read from Vite's import.meta.env
 */

// Vite environment type
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_BOT_USERNAME?: string;
  readonly MODE: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
}

// Helper to safely access import.meta.env
const getEnv = (): ImportMetaEnv => {
  if (typeof import.meta !== 'undefined' && import.meta.env) {
    return import.meta.env as ImportMetaEnv;
  }
  return { MODE: 'production', DEV: false, PROD: true };
};

const env = getEnv();

/**
 * API Configuration
 */
export const API = {
  /** Base URL for WebApp API endpoints */
  BASE_URL: env.VITE_API_URL || '/api/webapp',
  /** Base URL for Admin API endpoints */
  ADMIN_URL: '/api/admin',
  /** Request timeout in milliseconds */
  TIMEOUT: 30000,
  /** Retry attempts for failed requests */
  RETRY_ATTEMPTS: 3,
  /** Delay between retries in milliseconds */
  RETRY_DELAY: 1000,
} as const;

/**
 * Bot Configuration
 */
export const BOT = {
  /** Telegram bot username (without @) */
  USERNAME: env.VITE_BOT_USERNAME || window.__BOT_USERNAME || 'pvndora_ai_bot',
  /** Deep link base URL */
  DEEP_LINK: 'https://t.me/pvndora_ai_bot',
} as const;

/**
 * UI Configuration
 */
export const UI = {
  /** Boot sequence minimum duration in ms */
  BOOT_MIN_DURATION: 2500,
  /** HUD notification duration in ms */
  HUD_DURATION: 4000,
  /** Max HUD notifications visible at once */
  HUD_MAX_NOTIFICATIONS: 5,
  /** Background music volume (0-1) */
  MUSIC_VOLUME: 0.20,
  /** Animation transition duration in ms */
  TRANSITION_DURATION: 300,
  /** Debounce delay for search inputs in ms */
  SEARCH_DEBOUNCE: 300,
  /** Copy feedback duration (show "copied" state) in ms */
  COPY_FEEDBACK_DURATION: 2000,
  /** Success message display duration in ms */
  SUCCESS_MESSAGE_DURATION: 2000,
  /** Default timeout for retry operations in ms */
  RETRY_DELAY: 1000,
} as const;

/**
 * Pagination Configuration
 */
export const PAGINATION = {
  /** Default page size for lists */
  DEFAULT_LIMIT: 15,
  /** Leaderboard page size */
  LEADERBOARD_LIMIT: 15,
  /** Orders page size */
  ORDERS_LIMIT: 20,
  /** Referral network limit per level */
  REFERRAL_LIMIT: 50,
} as const;

/**
 * Cache Configuration
 */
export const CACHE = {
  /** Session storage key for boot state */
  BOOT_STATE_KEY: 'pvndora_booted',
  /** Local storage key for session token */
  SESSION_TOKEN_KEY: 'pvndora_session',
  /** Cache duration for products in ms */
  PRODUCTS_TTL: 5 * 60 * 1000, // 5 minutes
} as const;

/**
 * Feature Flags
 */
export const FEATURES = {
  /** Enable debug logging */
  DEBUG: env.DEV,
  /** Enable performance monitoring */
  PERFORMANCE_MONITORING: env.PROD,
  /** Enable error reporting */
  ERROR_REPORTING: env.PROD,
} as const;

/**
 * Payment Configuration
 */
export const PAYMENT = {
  /** Minimum withdrawal amount */
  MIN_WITHDRAWAL: 500,
  /** Default payment gateway */
  DEFAULT_GATEWAY: 'crystalpay',
  /** Payment timeout in seconds */
  PAYMENT_TIMEOUT: 600, // 10 minutes
} as const;

/**
 * Localization
 */
export const LOCALE = {
  /** Default language */
  DEFAULT_LANGUAGE: 'en',
  /** Supported languages */
  SUPPORTED_LANGUAGES: ['en', 'ru', 'de', 'es', 'fr', 'it', 'pt', 'uk', 'be'] as const,
  /** CIS languages (use RUB currency) */
  CIS_LANGUAGES: ['ru', 'be', 'kk', 'uk'] as const,
} as const;

/**
 * Get user's language code from Telegram or browser
 */
export function getLanguageCode(): string {
  const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
  const browserLang = navigator.language?.split('-')[0];
  return tgLang || browserLang || LOCALE.DEFAULT_LANGUAGE;
}

/**
 * Get currency based on language
 */
export function getCurrencyForLanguage(lang?: string): 'RUB' | 'USD' {
  const langCode = lang || getLanguageCode();
  return LOCALE.CIS_LANGUAGES.includes(langCode as any) ? 'RUB' : 'USD';
}

/**
 * Check if running inside Telegram WebApp
 */
export function isTelegramWebApp(): boolean {
  return !!window.Telegram?.WebApp?.initData;
}

export default {
  API,
  BOT,
  UI,
  PAGINATION,
  CACHE,
  FEATURES,
  PAYMENT,
  LOCALE,
  getLanguageCode,
  getCurrencyForLanguage,
  isTelegramWebApp,
};
