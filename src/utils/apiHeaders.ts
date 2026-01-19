/**
 * API Headers Utility
 *
 * Centralized logic for generating API request headers.
 * Supports both Telegram Mini App (initData) and web session (Bearer token).
 */

import { CACHE } from "../config";
import type { WebApp } from "../types/telegram";
import { localStorage } from "./storage";

export interface ApiHeaders {
  "Content-Type": string;
  "X-Init-Data"?: string;
  Authorization?: string;
}

/**
 * Get API headers with authentication.
 * Tries Telegram initData first, falls back to session token.
 *
 * @returns Headers object with Content-Type and authentication (X-Init-Data or Authorization)
 *
 * @example
 * ```ts
 * const headers = getApiHeaders();
 * // { 'Content-Type': 'application/json', 'X-Init-Data': '...' }
 * // or
 * // { 'Content-Type': 'application/json', 'Authorization': 'Bearer token' }
 * ```
 */
export function getApiHeaders(): ApiHeaders {
  const headers: ApiHeaders = {
    "Content-Type": "application/json",
  };

  // Try Telegram initData first (Mini App)
  const tgWebApp: WebApp | undefined =
    globalThis.window === undefined
      ? undefined
      : (globalThis as typeof globalThis & { Telegram?: { WebApp?: WebApp } }).Telegram?.WebApp;

  const initData = tgWebApp?.initData || "";

  if (initData) {
    headers["X-Init-Data"] = initData;
  } else {
    // Fallback to Bearer token (web session)
    const sessionToken = localStorage.get(CACHE.SESSION_TOKEN_KEY);
    if (sessionToken) {
      headers.Authorization = `Bearer ${sessionToken}`;
    }
  }

  return headers;
}

/**
 * Alias for getApiHeaders (for backward compatibility)
 * @deprecated Use getApiHeaders() instead
 */
export const getAuthHeaders = getApiHeaders;
