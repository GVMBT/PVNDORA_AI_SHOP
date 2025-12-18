/// <reference types="vite/client" />

/**
 * Vite Environment Type Definitions
 * 
 * Extends ImportMeta to include env property for Vite environment variables.
 */

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_BOT_USERNAME?: string;
  readonly MODE: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
  readonly BASE_URL: string;
  readonly SSR: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}


















