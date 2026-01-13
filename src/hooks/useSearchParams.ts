import { useMemo } from "react";

/**
 * Hook to parse URL search params and Telegram startapp
 * Uses single synchronous initialization to avoid timing issues
 */
export function useSearchParams(): URLSearchParams {
  // Single initialization path - compute everything synchronously
  const params = useMemo(() => {
    const p = new URLSearchParams(window.location.search);

    // Also check hash for Telegram Mini App params
    if (window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.slice(1));
      hashParams.forEach((value, key) => {
        if (!p.has(key)) {
          p.set(key, value);
        }
      });
    }

    // Decode Base64url startapp if present
    const telegramStartapp = p.get("tgWebAppStartParam");
    const urlStartapp = p.get("startapp");
    const startapp = telegramStartapp || urlStartapp;

    if (startapp) {
      // If already in our format (pay_ or product_), don't decode
      if (startapp.startsWith("pay_") || startapp.startsWith("product_")) {
        p.set("startapp", startapp);
      } else if (
        startapp.includes("_") &&
        !startapp.startsWith("pay_") &&
        !startapp.startsWith("product_")
      ) {
        // Already decoded format like "checkout" or other formats with underscores
        p.set("startapp", startapp);
      } else {
        // Try Base64url decode only if it doesn't look like our format
        try {
          const decoded = atob(startapp.replace(/-/g, "+").replace(/_/g, "/"));
          // Check if decoded result looks like our format
          if (
            decoded.startsWith("pay_") ||
            decoded.startsWith("product_") ||
            decoded.startsWith("checkout")
          ) {
            p.set("startapp", decoded);
          } else {
            // Not our format, keep original
            p.set("startapp", startapp);
          }
        } catch (e) {
          // Keep original if not Base64
          p.set("startapp", startapp);
        }
      }
    }

    return p;
  }, []); // Empty deps - only compute once on mount

  return params;
}

export default useSearchParams;
