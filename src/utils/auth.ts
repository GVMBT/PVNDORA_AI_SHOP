/**
 * Authentication Utilities
 *
 * Shared authentication logic for web and Telegram Mini App.
 */

import { API, CACHE } from "../config";
import { localStorage } from "./storage";
import { logger } from "./logger";
import { apiPost } from "./apiClient";

/**
 * Extract session_token from URL query and persist to localStorage.
 * Used for web login flow when Telegram initData is unavailable.
 *
 * @returns Extracted token or null if not found
 *
 * @example
 * ```ts
 * // URL: https://app.com/?session_token=abc123
 * const token = persistSessionTokenFromQuery(); // Returns 'abc123' and saves to localStorage
 * ```
 */
export function persistSessionTokenFromQuery(): string | null {
  if (globalThis.window === undefined) return null;
  try {
    const url = new URL(globalThis.location.href);
    const token = url.searchParams.get("session_token");
    if (token) {
      localStorage.set(CACHE.SESSION_TOKEN_KEY, token);
      // Remove token from URL to avoid leaking
      url.searchParams.delete("session_token");
      globalThis.history.replaceState({}, "", url.toString());
      return token;
    }
  } catch {
    /* ignore URL parsing issues */
  }
  return null;
}

/**
 * Verify session token with backend.
 * Returns session data if valid, null if invalid or error.
 */
export interface SessionVerificationResult {
  valid: boolean;
  user?: {
    id: number;
    first_name?: string;
    username?: string;
    [key: string]: unknown;
  };
}

/**
 * Verify session token with backend API
 *
 * @param token - Session token string to verify
 * @returns Promise resolving to SessionVerificationResult or null on error
 */
export async function verifySessionToken(token: string): Promise<SessionVerificationResult | null> {
  try {
    // Use apiClient for consistent error handling
    const data = await apiPost<SessionVerificationResult>("/auth/verify-session", {
      session_token: token,
    });
    return data;
  } catch (err) {
    logger.error("Session verification error", err);
    return null;
  }
}

/**
 * Get session token from localStorage
 *
 * @returns Session token string or null if not found
 */
export function getSessionToken(): string | null {
  return localStorage.get(CACHE.SESSION_TOKEN_KEY);
}

/**
 * Save session token to localStorage
 *
 * @param token - Session token string to save
 */
export function saveSessionToken(token: string): void {
  localStorage.set(CACHE.SESSION_TOKEN_KEY, token);
}

/**
 * Remove session token from localStorage
 *
 * Clears the stored session token, effectively logging out the user.
 */
export function removeSessionToken(): void {
  localStorage.remove(CACHE.SESSION_TOKEN_KEY);
}
