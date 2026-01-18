/**
 * Admin Realtime Hook
 *
 * Subscribes to admin.* events and refreshes admin data automatically.
 */

import { useRealtime } from "@upstash/realtime/client";
import { logger } from "../utils/logger";

interface AdminRealtimeCallbacks {
  onWithdrawalUpdate?: () => void;
  onOrderCreated?: () => void;
  onAccountingUpdate?: () => void;
}

export function useAdminRealtime(callbacks: AdminRealtimeCallbacks) {
  const { onWithdrawalUpdate, onOrderCreated, onAccountingUpdate } = callbacks;

  // Subscribe to withdrawal updates
  useRealtime({
    event: "admin.withdrawal.updated",
    onData: (data) => {
      logger.debug("Admin withdrawal updated via realtime", data);
      onWithdrawalUpdate?.();
    },
  });

  // Subscribe to new orders
  useRealtime({
    event: "admin.order.created",
    onData: (data) => {
      logger.debug("Admin order created via realtime", data);
      onOrderCreated?.();
    },
  });

  // Subscribe to accounting updates
  useRealtime({
    event: "admin.accounting.updated",
    onData: (data) => {
      logger.debug("Admin accounting updated via realtime", data);
      onAccountingUpdate?.();
    },
  });
}
