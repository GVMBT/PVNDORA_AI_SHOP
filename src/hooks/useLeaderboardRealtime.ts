/**
 * Leaderboard Realtime Hook
 *
 * Subscribes to leaderboard.updated events and refreshes leaderboard automatically.
 */

import { useRealtime } from "@upstash/realtime/client";
import { PAGINATION } from "../config";
import { logger } from "../utils/logger";
import { useLeaderboardTyped } from "./api/useLeaderboardApi";

export function useLeaderboardRealtime() {
  const { getLeaderboard } = useLeaderboardTyped();

  useRealtime({
    event: "leaderboard.updated",
    onData: (data) => {
      logger.debug("Leaderboard updated via realtime", data);
      // Refresh leaderboard (reload first page)
      getLeaderboard(PAGINATION.LEADERBOARD_LIMIT, 0, false).catch((err) => {
        logger.error("Failed to refresh leaderboard after realtime event", err);
      });
    },
  });
}
