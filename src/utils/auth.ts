/**
 * Authentication Utilities
 * 
 * Shared authentication logic for web and Telegram Mini App.
 */

/**
 * Extract session_token from URL query and persist to localStorage.
 * Used for web login flow when Telegram initData is unavailable.
 */
export function persistSessionTokenFromQuery(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const url = new URL(window.location.href);
    const token = url.searchParams.get('session_token');
    if (token) {
      window.localStorage?.setItem('pvndora_session', token);
      // Remove token from URL to avoid leaking
      url.searchParams.delete('session_token');
      window.history.replaceState({}, '', url.toString());
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
export async function verifySessionToken(token: string): Promise<{ valid: boolean; user?: any } | null> {
  try {
    const response = await fetch('/api/webapp/auth/verify-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_token: token }),
    });

    // Check if response is ok before parsing JSON
    if (!response.ok) {
      // Try to parse error message if available
      try {
        const errorData = await response.json();
        console.error('Session verification failed:', errorData);
      } catch {
        // If not JSON, log response text
        const text = await response.text();
        console.error('Session verification failed with non-JSON response:', text.substring(0, 100));
      }
      return null;
    }

    const data = await response.json();
    return data;
  } catch (err) {
    console.error('Session verification error:', err);
    return null;
  }
}

/**
 * Get session token from localStorage.
 */
export function getSessionToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage?.getItem('pvndora_session') || null;
}

/**
 * Save session token to localStorage.
 */
export function saveSessionToken(token: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage?.setItem('pvndora_session', token);
}

/**
 * Remove session token from localStorage.
 */
export function removeSessionToken(): void {
  if (typeof window === 'undefined') return;
  window.localStorage?.removeItem('pvndora_session');
}
