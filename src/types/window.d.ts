/**
 * Window Global Type Extensions
 *
 * Type definitions for global window properties used by third-party scripts.
 */

declare global {
  interface Window {
    /**
     * Telegram Login Widget callback
     * Set by telegram-widget.js script dynamically
     */
    onTelegramAuth?: (user: {
      id: number;
      first_name: string;
      last_name?: string;
      username?: string;
      photo_url?: string;
      auth_date: number;
      hash: string;
    }) => void;

    /**
     * Custom bot username override (for development/testing)
     */
    __BOT_USERNAME?: string;

    /**
     * WebKit prefixed AudioContext (for Safari compatibility)
     */
    webkitAudioContext?: typeof AudioContext;
  }
}

export {};
