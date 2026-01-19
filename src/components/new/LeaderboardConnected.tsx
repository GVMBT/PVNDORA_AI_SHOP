/**
 * LeaderboardConnected
 *
 * Connected version of Leaderboard component with real API data.
 * Supports infinite scroll pagination and period filtering.
 */

import type React from "react";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import { PAGINATION } from "../../config";
import { useLeaderboardTyped } from "../../hooks/useApiTyped";
import { useLeaderboardRealtime } from "../../hooks/useLeaderboardRealtime";
import { useLocale } from "../../hooks/useLocale";
import Leaderboard from "./Leaderboard";

interface LeaderboardConnectedProps {
  onBack: () => void;
}

const LeaderboardConnected: React.FC<LeaderboardConnectedProps> = ({ onBack }) => {
  const { leaderboard, getLeaderboard, loadMore, hasMore, loading, error, reset } =
    useLeaderboardTyped();
  const { t } = useLocale();
  const [isInitialized, setIsInitialized] = useState(false);
  const [activeFilter, setActiveFilter] = useState<"weekly" | "all_time">("all_time");
  const loadingRef = useRef(false);

  useEffect(() => {
    const init = async () => {
      await getLeaderboard(PAGINATION.LEADERBOARD_LIMIT, 0, false);
      setIsInitialized(true);
    };
    init();
  }, [getLeaderboard]);

  // Real-time updates for leaderboard
  useLeaderboardRealtime();

  // Handle filter change - reset and reload with new period
  const handleFilterChange = useCallback(
    async (newFilter: "weekly" | "all_time") => {
      if (newFilter === activeFilter) {
        return;
      }

      setActiveFilter(newFilter);
      reset?.(); // Reset the loaded offsets tracker
      setIsInitialized(false);

      // Map filter to API period (reserved for future API update)
      // const period = newFilter === "weekly" ? "week" : "all";
      await getLeaderboard(15, 0, false);
      setIsInitialized(true);
    },
    [activeFilter, getLeaderboard, reset]
  );

  // Infinite scroll handler
  const handleLoadMore = useCallback(async () => {
    if (loadingRef.current || !hasMore) {
      return;
    }
    loadingRef.current = true;
    await loadMore();
    loadingRef.current = false;
  }, [loadMore, hasMore]);

  // Loading state (initial only)
  if (!isInitialized) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-2 border-pandora-cyan border-t-transparent" />
          <div className="font-mono text-gray-500 text-xs uppercase tracking-widest">
            {t("common.loadingLeaderboard")}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error && leaderboard.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="max-w-md text-center">
          <div className="mb-4 text-6xl text-red-500">⚠</div>
          <div className="mb-2 font-mono text-red-400 text-sm">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            className="mt-6 border border-white/20 bg-white/10 px-6 py-2 font-mono text-white text-xs uppercase transition-colors hover:bg-white/20"
            onClick={() => getLeaderboard(15, 0, false)}
            type="button"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Leaderboard
      activeFilter={activeFilter}
      hasMore={hasMore}
      isLoadingMore={loading && isInitialized}
      leaderboardData={leaderboard}
      onBack={onBack}
      onFilterChange={handleFilterChange}
      onLoadMore={handleLoadMore}
    />
  );
};

export default memo(LeaderboardConnected);
