/**
 * Profile Realtime Hook
 *
 * Subscribes to profile.updated events and refreshes profile data automatically.
 */

import { useRealtime } from "@upstash/realtime/client";
import { logger } from "../utils/logger";
import { useProfileTyped } from "./api/useProfileApi";

export function useProfileRealtime() {
  const { getProfile } = useProfileTyped();

  useRealtime({
    event: "profile.updated",
    onData: (data) => {
      logger.debug("Profile updated via realtime", data);
      // Refresh profile data
      getProfile().catch((err) => {
        logger.error("Failed to refresh profile after realtime event", err);
      });
    },
  });
}
