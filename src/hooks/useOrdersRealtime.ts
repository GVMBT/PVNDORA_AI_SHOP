/**
 * Orders Realtime Hook
 *
 * Subscribes to order.status.changed events and refreshes orders list automatically.
 */

import { useRealtime } from "@upstash/realtime/client";
import { useOrdersTyped } from "./useApiTyped";
import { logger } from "../utils/logger";

export function useOrdersRealtime() {
  const { getOrders } = useOrdersTyped();

  useRealtime({
    event: "order.status.changed",
    onData: (data) => {
      logger.debug("Order status changed via realtime", data);
      // Refresh orders list
      getOrders().catch((err) => {
        logger.error("Failed to refresh orders after realtime event", err);
      });
    },
  });
}
