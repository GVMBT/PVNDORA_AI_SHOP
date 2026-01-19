/**
 * OrdersConnected
 *
 * Connected version of Orders component with real API data.
 */

import type React from "react";
import { memo, useCallback, useEffect, useState } from "react";
import { useOrdersTyped, useReviewsTyped } from "../../hooks/useApiTyped";
import { useLocale } from "../../hooks/useLocale";
import { useOrdersRealtime } from "../../hooks/useOrdersRealtime";
import { logger } from "../../utils/logger";
import Orders, { type RefundContext } from "./Orders";

interface OrdersConnectedProps {
  onBack: () => void;
  onOpenSupport?: (context?: RefundContext) => void;
}

const OrdersConnected: React.FC<OrdersConnectedProps> = ({ onBack, onOpenSupport }) => {
  const { orders, getOrders, loading, error } = useOrdersTyped();
  const { submitReview } = useReviewsTyped();
  const { t } = useLocale();
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const init = async () => {
      await getOrders();
      setIsInitialized(true);
    };
    init();
  }, [getOrders]);

  // Real-time updates for orders
  useOrdersRealtime();

  const handleSubmitReview = useCallback(
    async (orderId: string, rating: number, text?: string, orderItemId?: string) => {
      try {
        // Pass orderItemId so backend knows which specific product to review
        await submitReview(orderId, rating, text, undefined, orderItemId);
        // Refresh orders to update hasReview status
        await getOrders();
      } catch (err) {
        logger.error(
          "Failed to submit review",
          err instanceof Error ? err : new Error(String(err))
        );
      }
    },
    [submitReview, getOrders]
  );

  // Loading state
  if (!isInitialized || loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-2 border-pandora-cyan border-t-transparent" />
          <div className="font-mono text-gray-500 text-xs uppercase tracking-widest">
            {t("common.loadingOrders")}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="max-w-md text-center">
          <div className="mb-4 text-6xl text-red-500">⚠</div>
          <div className="mb-2 font-mono text-red-400 text-sm">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            className="mt-6 border border-white/20 bg-white/10 px-6 py-2 font-mono text-white text-xs uppercase transition-colors hover:bg-white/20"
            onClick={() => getOrders()}
            type="button"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Orders
      onBack={onBack}
      onOpenSupport={onOpenSupport}
      onSubmitReview={handleSubmitReview}
      orders={orders}
    />
  );
};

export default memo(OrdersConnected);
