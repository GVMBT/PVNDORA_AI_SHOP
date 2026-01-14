/**
 * OrdersConnected
 *
 * Connected version of Orders component with real API data.
 */

import type React from "react";
import { memo, useCallback, useEffect, useState } from "react";
import { useOrdersTyped, useReviewsTyped } from "../../hooks/useApiTyped";
import { useLocale } from "../../hooks/useLocale";
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            {t("common.loadingOrders")}
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠</div>
          <div className="font-mono text-sm text-red-400 mb-2">CONNECTION_ERROR</div>
          <p className="text-gray-500 text-sm">{error}</p>
          <button
            type="button"
            onClick={() => getOrders()}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Orders
      orders={orders}
      onBack={onBack}
      onOpenSupport={onOpenSupport}
      onSubmitReview={handleSubmitReview}
    />
  );
};

export default memo(OrdersConnected);
