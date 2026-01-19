/**
 * Leaderboard API Hook
 *
 * Type-safe hook for fetching leaderboard with pagination.
 * Uses user's preferred currency from context.
 */

import { useCallback, useRef, useState } from "react";
import { adaptLeaderboard } from "../../adapters";
import { PAGINATION } from "../../config";
import { useLocaleContext } from "../../contexts/LocaleContext";
import type { APILeaderboardResponse } from "../../types/api";
import type { LeaderboardUser } from "../../types/component";
import { logger } from "../../utils/logger";
import { useApi } from "../useApi";

export function useLeaderboardTyped() {
  const { get, loading, error } = useApi();
  const { currency: contextCurrency } = useLocaleContext();
  const [leaderboard, setLeaderboard] = useState<LeaderboardUser[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [currentOffset, setCurrentOffset] = useState(0);
  const loadedOffsetsRef = useRef<Set<number>>(new Set());

  const getLeaderboard = useCallback(
    async (
      limit: number = PAGINATION.LEADERBOARD_LIMIT,
      offset = 0,
      append = false
    ): Promise<LeaderboardUser[]> => {
      if (append && loadedOffsetsRef.current.has(offset)) {
        logger.debug(`[Leaderboard] Skipping duplicate request for offset ${offset}`);
        return [];
      }

      try {
        const response: APILeaderboardResponse = await get(
          `/leaderboard?limit=${limit}&offset=${offset}`
        );
        const telegramUser = (
          globalThis as typeof globalThis & {
            Telegram?: {
              WebApp?: {
                initDataUnsafe?: {
                  user?: { first_name?: string; username?: string; photo_url?: string };
                };
              };
            };
          }
        ).Telegram?.WebApp?.initDataUnsafe?.user;
        // Use currency from context (user preference) instead of language-based detection
        const currency = contextCurrency || "USD";
        const adapted = adaptLeaderboard(response, telegramUser?.id?.toString(), currency);

        loadedOffsetsRef.current.add(offset);

        setHasMore(response.has_more ?? adapted.length === limit);
        setCurrentOffset(offset + adapted.length);

        if (append && offset > 0) {
          setLeaderboard((prev) => {
            const combined = [...prev, ...adapted];
            const seenRanks = new Set<number>();
            const unique = combined.filter((user) => {
              if (seenRanks.has(user.rank)) {
                return false;
              }
              seenRanks.add(user.rank);
              return true;
            });
            return unique.sort((a, b) => a.rank - b.rank);
          });
        } else {
          loadedOffsetsRef.current.clear();
          loadedOffsetsRef.current.add(offset);
          setLeaderboard(adapted);
        }

        return adapted;
      } catch (err) {
        logger.error("Failed to fetch leaderboard", err);
        return [];
      }
    },
    [get, contextCurrency]
  );

  const loadMore = useCallback(() => {
    if (!hasMore || loading) {
      return Promise.resolve();
    }
    return getLeaderboard(PAGINATION.LEADERBOARD_LIMIT, currentOffset, true);
  }, [getLeaderboard, hasMore, loading, currentOffset]);

  const reset = useCallback(() => {
    loadedOffsetsRef.current.clear();
    setLeaderboard([]);
    setCurrentOffset(0);
    setHasMore(true);
  }, []);

  return { leaderboard, getLeaderboard, loadMore, hasMore, loading, error, reset };
}
