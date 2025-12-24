/**
 * useTimeoutState Hook
 * 
 * Manages temporary state that automatically resets after a timeout.
 * Useful for feedback states like "copied", "success", etc.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { UI } from '../config';

interface UseTimeoutStateOptions {
  /** Timeout duration in ms (default: UI.COPY_FEEDBACK_DURATION) */
  timeout?: number;
  /** Callback when timeout expires */
  onTimeout?: () => void;
}

/**
 * Hook for managing temporary state with auto-reset
 * 
 * @example
 * const [copiedId, setCopiedId] = useTimeoutState<string | null>(null);
 * // Set value and it will auto-reset after timeout
 * setCopiedId('some-id');
 */
export function useTimeoutState<T>(
  initialValue: T,
  options: UseTimeoutStateOptions = {}
): [T, (value: T) => void] {
  const { timeout = UI.COPY_FEEDBACK_DURATION, onTimeout } = options;
  const [state, setState] = useState<T>(initialValue);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const setValue = useCallback(
    (value: T) => {
      // Clear existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      // Set new state
      setState(value);

      // Only set timeout if value is truthy (not null/undefined/empty)
      if (value !== null && value !== undefined && value !== '' && value !== false) {
        timeoutRef.current = setTimeout(() => {
          setState(initialValue);
          onTimeout?.();
        }, timeout);
      }
    },
    [initialValue, timeout, onTimeout]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return [state, setValue];
}

































