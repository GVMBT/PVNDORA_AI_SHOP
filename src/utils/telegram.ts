/**
 * Telegram WebApp Utilities
 * 
 * Low-level utilities for Telegram WebApp SDK operations.
 * For React components, use useTelegram() hook instead.
 */

/**
 * Get Telegram WebApp instance (if available)
 */
import type { WebApp } from '../types/telegram';

export function getTelegramWebApp(): WebApp | undefined {
  if (typeof window === 'undefined') return undefined;
  return window.Telegram?.WebApp;
}

/**
 * Get Telegram initData (for API requests)
 * 
 * @returns Telegram initData string or empty string if not available
 */
export function getTelegramInitData(): string {
  const tg = getTelegramWebApp();
  return tg?.initData || '';
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
 * Expands the WebApp to full screen height.
 */
export function requestFullscreen(): void {
  const tg = getTelegramWebApp();
  // requestFullscreen is available in newer Bot API versions
  if (tg && 'requestFullscreen' in tg) {
    (tg as unknown as { requestFullscreen: () => void }).requestFullscreen();
  }
}

/**
 * Expand WebApp to full height
 */
export function expandWebApp(): void {
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



