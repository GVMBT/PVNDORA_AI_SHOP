/**
 * Telegram WebApp Utilities
 *
 * Low-level utilities for Telegram WebApp SDK operations.
 * For React components, use useTelegram() hook instead.
 */

import { expandViewport, requestFullscreen as sdkRequestFullscreen } from "@telegram-apps/sdk";
import type { WebApp } from "../types/telegram";

export function getTelegramWebApp(): WebApp | undefined {
  if (globalThis.window === undefined) return undefined;
  return (globalThis as typeof globalThis & { Telegram?: { WebApp?: WebApp } }).Telegram?.WebApp;
}

/**
 * Get Telegram initData (for API requests)
 *
 * @returns Telegram initData string or empty string if not available
 */
export function getTelegramInitData(): string {
  const tg = getTelegramWebApp();
  return tg?.initData || "";
}

/**
 * Get Telegram user data (unsafe, for development only)
 *
 * @returns Telegram user object or null if not available
 * @warning This uses initDataUnsafe which is not cryptographically verified
 */
export function getTelegramUser(): { id: number; language_code?: string } | null {
  const tg = getTelegramWebApp();
  const user = tg?.initDataUnsafe?.user;
  if (!user) return null;
  return { id: user.id, language_code: user.language_code };
}

/**
 * Check if running in Telegram WebApp
 *
 * @returns true if Telegram WebApp is available, false otherwise
 */
export function isTelegramWebApp(): boolean {
  return !!getTelegramWebApp();
}

/**
 * Get start parameter from Telegram WebApp
 *
 * @returns Start parameter string or null if not available
 */
export function getStartParam(): string | null {
  const tg = getTelegramWebApp();
  return tg?.initDataUnsafe?.start_param || null;
}

/**
 * Request fullscreen (for better UX in Telegram)
 *
 * Uses modern @telegram-apps/sdk for fullscreen support.
 * Automatically checks availability and handles errors gracefully.
 */
export async function requestFullscreen(): Promise<void> {
  try {
    // Use modern SDK if available
    if (sdkRequestFullscreen.isAvailable()) {
      await sdkRequestFullscreen();
      return;
    }
  } catch {
    // SDK not available or not in Telegram context, fallback to legacy
  }

  // Fallback to legacy WebApp API
  const tg = getTelegramWebApp();
  if (!tg) return;

  // Check Telegram WebApp version - requestFullscreen not supported in 6.0+
  const version = tg.version || "";
  if (version && Number.parseFloat(version) >= 6) {
    // requestFullscreen is not supported in version 6.0+, skip
    return;
  }

  // Check if method exists
  if (!("requestFullscreen" in tg)) return;

  // Try to call requestFullscreen (may throw if not configured in BotFather)
  try {
    (tg as unknown as { requestFullscreen: () => void }).requestFullscreen();
  } catch {
    // Silently ignore - method not available or not configured
  }
}

/**
 * Expand WebApp to full height
 *
 * Uses modern @telegram-apps/sdk expandViewport if available,
 * falls back to legacy expand() method.
 */
export async function expandWebApp(): Promise<void> {
  try {
    // Use modern SDK if available
    if (expandViewport.isAvailable()) {
      expandViewport();
      return;
    }
  } catch {
    // SDK not available, fallback to legacy
  }

  // Fallback to legacy WebApp API
  const tg = getTelegramWebApp();
  if (tg?.expand) {
    tg.expand();
  }
}

/**
 * Ready WebApp (call on initialization)
 *
 * Notifies Telegram that the app is ready. Should be called once on app load.
 */
export function readyWebApp(): void {
  const tg = getTelegramWebApp();
  if (tg?.ready) {
    tg.ready();
  }
}
