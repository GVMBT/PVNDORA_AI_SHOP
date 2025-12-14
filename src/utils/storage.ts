/**
 * Storage Utilities
 * 
 * Centralized storage access for localStorage and sessionStorage.
 * Provides type-safe wrappers with error handling.
 */

/**
 * Session storage operations
 */
export const sessionStorage = {
  /**
   * Get item from sessionStorage
   */
  get: (key: string): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      return window.sessionStorage.getItem(key);
    } catch (err) {
      console.warn(`Failed to get sessionStorage item "${key}":`, err);
      return null;
    }
  },

  /**
   * Set item in sessionStorage
   */
  set: (key: string, value: string): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      window.sessionStorage.setItem(key, value);
      return true;
    } catch (err) {
      console.warn(`Failed to set sessionStorage item "${key}":`, err);
      return false;
    }
  },

  /**
   * Remove item from sessionStorage
   */
  remove: (key: string): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      window.sessionStorage.removeItem(key);
      return true;
    } catch (err) {
      console.warn(`Failed to remove sessionStorage item "${key}":`, err);
      return false;
    }
  },

  /**
   * Clear all sessionStorage
   */
  clear: (): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      window.sessionStorage.clear();
      return true;
    } catch (err) {
      console.warn('Failed to clear sessionStorage:', err);
      return false;
    }
  },
};

/**
 * Local storage operations
 */
export const localStorage = {
  /**
   * Get item from localStorage
   */
  get: (key: string): string | null => {
    if (typeof window === 'undefined') return null;
    try {
      return window.localStorage.getItem(key);
    } catch (err) {
      console.warn(`Failed to get localStorage item "${key}":`, err);
      return null;
    }
  },

  /**
   * Set item in localStorage
   */
  set: (key: string, value: string): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      window.localStorage.setItem(key, value);
      return true;
    } catch (err) {
      console.warn(`Failed to set localStorage item "${key}":`, err);
      return false;
    }
  },

  /**
   * Remove item from localStorage
   */
  remove: (key: string): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      window.localStorage.removeItem(key);
      return true;
    } catch (err) {
      console.warn(`Failed to remove localStorage item "${key}":`, err);
      return false;
    }
  },

  /**
   * Clear all localStorage
   */
  clear: (): boolean => {
    if (typeof window === 'undefined') return false;
    try {
      window.localStorage.clear();
      return true;
    } catch (err) {
      console.warn('Failed to clear localStorage:', err);
      return false;
    }
  },
};
