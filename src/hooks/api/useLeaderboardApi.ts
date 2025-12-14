/**
 * Leaderboard API Hook
 * 
 * Type-safe hook for fetching leaderboard with pagination.
 */

import React, { useState, useCallback, useRef } from 'react';
import { useApi } from '../useApi';
import type { APILeaderboardResponse } from '../../types/api';
import type { LeaderboardUser } from '../../types/component';
import { adaptLeaderboard } from '../../adapters';

export function useLeaderboardTyped() {
  const { get, loading, error } = useApi();
  const [leaderboard, setLeaderboard] = useState<LeaderboardUser[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [currentOffset, setCurrentOffset] = useState(0);
  const loadedOffsetsRef = useRef<Set<number>>(new Set());

  const getLeaderboard = useCallback(async (limit: number = 15, offset: number = 0, append: boolean = false): Promise<LeaderboardUser[]> => {
    if (append && loadedOffsetsRef.current.has(offset)) {
      console.log(`[Leaderboard] Skipping duplicate request for offset ${offset}`);
      return [];
    }
    
    try {
      const response: APILeaderboardResponse = await get(`/leaderboard?limit=${limit}&offset=${offset}`);
      const telegramUser = (window as any).Telegram?.WebApp?.initDataUnsafe?.user;
      const lang = telegramUser?.language_code || navigator.language?.split('-')[0] || 'en';
      const currency = (lang === 'ru' || lang === 'be' || lang === 'kk') ? 'RUB' : 'USD';
      const adapted = adaptLeaderboard(response, telegramUser?.id?.toString(), currency);
      
      loadedOffsetsRef.current.add(offset);
      
      const responseHasMore = (response as any).has_more;
      setHasMore(responseHasMore ?? adapted.length === limit);
      setCurrentOffset(offset + adapted.length);
      
      if (append && offset > 0) {
        setLeaderboard(prev => {
          const combined = [...prev, ...adapted];
          const seenRanks = new Set<number>();
          const unique = combined.filter(user => {
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
      console.error('Failed to fetch leaderboard:', err);
      return [];
    }
  }, [get]);

  const loadMore = useCallback(async () => {
    if (!hasMore || loading) return;
    return getLeaderboard(15, currentOffset, true);
  }, [getLeaderboard, hasMore, loading, currentOffset]);

  const reset = useCallback(() => {
    loadedOffsetsRef.current.clear();
    setLeaderboard([]);
    setCurrentOffset(0);
    setHasMore(true);
  }, []);

  return { leaderboard, getLeaderboard, loadMore, hasMore, loading, error, reset };
}
