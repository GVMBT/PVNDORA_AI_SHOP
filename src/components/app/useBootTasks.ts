/**
 * Boot Tasks Hook
 *
 * Defines the boot sequence tasks for the application.
 * These run real operations: auth check, data loading, etc.
 */

import { useMemo } from "react";
import { AudioEngine } from "../../lib/AudioEngine";
import {
  getSessionToken,
  persistSessionTokenFromQuery,
  removeSessionToken,
  verifySessionToken,
} from "../../utils/auth";
import { logger } from "../../utils/logger";
import { getTelegramInitData } from "../../utils/telegram";
import type { BootTask } from "../new";

interface UseBootTasksProps {
  getProducts: () => Promise<unknown>;
  getCart: () => Promise<unknown>;
  getProfile: () => Promise<unknown>;
}

export function useBootTasks({ getProducts, getCart, getProfile }: UseBootTasksProps): BootTask[] {
  return useMemo(
    () => [
      {
        id: "audio",
        label: "Initializing audio subsystem...",
        successLabel: "Audio engine: ONLINE",
        execute: async () => {
          AudioEngine.init();
          await AudioEngine.resume();
          AudioEngine.boot();
          return true;
        },
      },
      {
        id: "auth",
        label: "Verifying operator credentials...",
        successLabel: "Operator authenticated",
        errorLabel: "Authentication required",
        critical: false,
        execute: async () => {
          persistSessionTokenFromQuery();

          const initData = getTelegramInitData();
          if (initData) {
            return { authenticated: true, source: "telegram" };
          }

          const sessionToken = getSessionToken();
          if (sessionToken) {
            const result = await verifySessionToken(sessionToken);
            if (result?.valid) {
              return { authenticated: true, source: "session" };
            }
            removeSessionToken();
          }

          return { authenticated: false };
        },
      },
      {
        id: "catalog",
        label: "Syncing inventory database...",
        successLabel: "Product catalog loaded",
        execute: async () => {
          const products = await getProducts();
          return { productCount: products?.length || 0 };
        },
      },
      {
        id: "cart",
        label: "Loading operator payload...",
        successLabel: "Cart data synchronized",
        execute: async () => {
          const cart = await getCart();
          return { itemCount: cart?.items?.length || 0 };
        },
      },
      {
        id: "profile",
        label: "Fetching operator profile...",
        successLabel: "Profile data cached",
        errorLabel: "Profile unavailable",
        critical: false,
        execute: async () => {
          try {
            const profileData = await getProfile();
            return {
              loaded: !!profileData,
              username: profileData?.handle || null,
              balance: profileData?.balance || 0,
            };
          } catch (e) {
            logger.warn("[Boot] Profile fetch failed", e);
            return { loaded: false };
          }
        },
      },
      {
        id: "prefetch",
        label: "Caching static resources...",
        successLabel: "Resources cached",
        execute: async () => {
          // Noise texture is now inline SVG, no external resources to prefetch
          return true;
        },
      },
    ],
    [getProducts, getCart, getProfile]
  );
}
