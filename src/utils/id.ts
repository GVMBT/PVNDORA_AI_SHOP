/**
 * ID Generation Utilities
 * 
 * Provides reliable ID generation methods for UI components.
 * Prefer crypto.randomUUID() when available, fallback to timestamp-based IDs.
 */

/**
 * Generate a unique ID for UI components (non-cryptographic)
 * Uses crypto.randomUUID() when available, otherwise falls back to timestamp-based ID
 */
export function generateId(prefix = 'id'): string {
  // Use crypto.randomUUID() if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  
  // Fallback: timestamp + random suffix
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 9);
  return `${prefix}-${timestamp}-${random}`;
}

/**
 * Generate a short ID (for compact UI use)
 * Format: prefix-XXXXX (9 chars total including prefix)
 */
export function generateShortId(prefix = 'id'): string {
  const random = Math.random().toString(36).substring(2, 7);
  return `${prefix}-${random}`;
}

/**
 * Generate a hash-like ID (for document hashes, etc.)
 * Format: uppercase alphanumeric string
 */
export function generateHashId(length = 12): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    // Use crypto.getRandomValues for better randomness
    const bytes = new Uint8Array(length);
    crypto.getRandomValues(bytes);
    for (let i = 0; i < length; i++) {
      result += chars[bytes[i] % chars.length];
    }
  } else {
    // Fallback to Math.random
    for (let i = 0; i < length; i++) {
      result += chars[Math.floor(Math.random() * chars.length)];
    }
  }
  return result;
}



