/**
 * Clipboard Hook
 *
 * Centralized clipboard operations with visual feedback.
 */

import { useCallback, useRef, useState } from "react";
import { logger } from "../utils/logger";

interface UseClipboardReturn {
  copy: (text: string) => Promise<boolean>;
  copied: boolean;
  reset: () => void;
}

/**
 * Hook for clipboard operations with visual feedback
 *
 * Provides a copy function and copied state that automatically resets after timeout.
 *
 * @param timeout - Time in ms to show "copied" state (default: 2000)
 * @returns Object with copy function, copied state, and reset function
 *
 * @example
 * ```ts
 * const { copy, copied } = useClipboard();
 *
 * <button onClick={() => copy('text to copy')}>
 *   {copied ? 'Copied!' : 'Copy'}
 * </button>
 * ```
 */
export function useClipboard(timeout: number = 2000): UseClipboardReturn {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      if (!text || typeof text !== "string") {
        logger.warn("Invalid text for clipboard copy", { text });
        return false;
      }

      try {
        // Clear existing timeout
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }

        await navigator.clipboard.writeText(text);
        setCopied(true);

        // Reset after timeout
        timeoutRef.current = setTimeout(() => {
          setCopied(false);
          timeoutRef.current = null;
        }, timeout);

        return true;
      } catch (err) {
        logger.error("Failed to copy to clipboard", err);
        setCopied(false);
        return false;
      }
    },
    [timeout]
  );

  const reset = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setCopied(false);
  }, []);

  return { copy, copied, reset };
}

export default useClipboard;
