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

  // Handle filter change - reset and reload with new period
  const handleFilterChange = useCallback(
    async (newFilter: "weekly" | "all_time") => {
      if (newFilter === activeFilter) return;

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
    if (loadingRef.current || !hasMore) return;
    loadingRef.current = true;
    await loadMore();
    loadingRef.current = false;
  }, [loadMore, hasMore]);

  // Loading state (initial only)
  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            {t("common.loadingLeaderboard")}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error && leaderboard.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠</div>
          <div className="font-mono text-sm text-red-400 mb-2">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            type="button"
            onClick={() => getLeaderboard(15, 0, false)}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Leaderboard
      leaderboardData={leaderboard}
      onBack={onBack}
      onLoadMore={handleLoadMore}
      hasMore={hasMore}
      isLoadingMore={loading && isInitialized}
      onFilterChange={handleFilterChange}
      activeFilter={activeFilter}
    />
  );
};

export default memo(LeaderboardConnected);
