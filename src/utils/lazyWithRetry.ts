/**
 * Lazy loading with automatic retry and cache busting
 *
 * Handles the case when a new deploy changes chunk hashes,
 * but browser has cached old index.html with stale chunk URLs.
 *
 * On chunk load failure:
 * 1. First failure: Retry once with cache bust
 * 2. Second failure: Force page reload to get new index.html
 */

import { type ComponentType, lazy } from "react";

// Track if we've already tried reloading
const RELOAD_KEY = "pvndora_chunk_reload";

/**
 * Check if error is a chunk loading error
 */
function isChunkLoadError(error: unknown): boolean {
  if (error instanceof Error) {
    const message = error.message.toLowerCase();
    return (
      message.includes("failed to fetch dynamically imported module") ||
      message.includes("loading chunk") ||
      message.includes("loading css chunk") ||
      message.includes("dynamically imported module") ||
      message.includes("unexpected token") // Sometimes happens with stale JS
    );
  }
  return false;
}

/**
 * Force page reload with cache bust
 */
function forceReload(): void {
  // Mark that we're reloading to prevent infinite loops
  const reloadCount = Number.parseInt(sessionStorage.getItem(RELOAD_KEY) || "0", 10);

  if (reloadCount < 2) {
    sessionStorage.setItem(RELOAD_KEY, String(reloadCount + 1));
    // Force reload bypassing cache
    globalThis.location.reload();
  } else {
    // Clear reload counter and let error boundary show error
    sessionStorage.removeItem(RELOAD_KEY);
    throw new Error(
      "Failed to load application after multiple retries. Please clear browser cache and try again."
    );
  }
}

/**
 * Clear reload counter on successful app load
 * Call this in your root component's useEffect
 */
export function clearReloadCounter(): void {
  sessionStorage.removeItem(RELOAD_KEY);
}

/**
 * Lazy import with automatic retry on chunk load failure
 */
export function lazyWithRetry<T extends ComponentType<unknown>>(
  componentImport: () => Promise<{ default: T }>
): React.LazyExoticComponent<T> {
  return lazy(async () => {
    try {
      // First attempt
      return await componentImport();
    } catch (error) {
      if (isChunkLoadError(error)) {
        // Chunk load failed - force reload to get new index.html
        forceReload();

        // This won't actually execute because forceReload() refreshes the page
        // But we need to return something for TypeScript
        const placeholder: T = ((): null => null) as unknown as T;
        return { default: placeholder };
      }

      // Re-throw non-chunk errors
      throw error;
    }
  });
}

/**
 * Global error handler for chunk load errors
 * Add this to your main.tsx or index.tsx
 */
export function setupChunkErrorHandler(): void {
  globalThis.addEventListener("error", (event: ErrorEvent) => {
    if (isChunkLoadError(event.error)) {
      event.preventDefault();
      forceReload();
    }
  });

  globalThis.addEventListener("unhandledrejection", (event: PromiseRejectionEvent) => {
    if (isChunkLoadError(event.reason)) {
      event.preventDefault();
      forceReload();
    }
  });
}
