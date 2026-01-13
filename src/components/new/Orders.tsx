import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { ArrowLeft, Box, Package, Terminal } from "lucide-react";
import { logger } from "../../utils/logger";
import { useClipboard } from "../../hooks/useClipboard";
import { useTimeoutState } from "../../hooks/useTimeoutState";
import { useLocale } from "../../hooks/useLocale";
import OrderCard, { type OrderData } from "./OrderCard";
import type { RefundContext } from "./OrderCard";
import OrderReviewModal from "./OrderReviewModal";

// Re-export types for backward compatibility
export type { OrderData } from "./OrderCard";
export type { OrderItemData } from "./OrderItem";
export type { RefundContext } from "./OrderCard";

interface OrdersProps {
  orders?: OrderData[];
  onBack: () => void;
  onOpenSupport?: (context?: RefundContext) => void;
  onSubmitReview?: (
    orderId: string,
    rating: number,
    text?: string,
    orderItemId?: string
  ) => Promise<void>;
}

const Orders: React.FC<OrdersProps> = ({
  orders: propOrders,
  onBack,
  onOpenSupport,
  onSubmitReview,
}) => {
  const { t } = useLocale();
  // Use provided orders - NO MOCK fallback
  const ordersData = propOrders || [];
  const [activeTab, setActiveTab] = useState<"all" | "active" | "log">("all");
  const [copiedId, setCopiedId] = useTimeoutState<number | string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<(number | string)[]>([]);
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set());

  // Review State - use ordersData as initial state when provided
  const [ordersState, setOrdersState] = useState<OrderData[]>(ordersData as OrderData[]);
  const [reviewModal, setReviewModal] = useState<{
    isOpen: boolean;
    itemId: number | string | null;
    itemName: string;
    orderId: string | null;
  }>({
    isOpen: false,
    itemId: null,
    itemName: "",
    orderId: null,
  });
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sync with prop changes
  useEffect(() => {
    if (propOrders) {
      setOrdersState(propOrders);
    }
  }, [propOrders]);

  const { copy: copyToClipboard } = useClipboard();

  const handleCopy = useCallback(
    async (text: string, id: number | string) => {
      const success = await copyToClipboard(text);
      if (success) {
        setCopiedId(id);
      }
    },
    [copyToClipboard, setCopiedId]
  );

  const toggleReveal = useCallback((id: number | string) => {
    setRevealedKeys((prev) => {
      if (prev.includes(id)) {
        return prev.filter((k) => k !== id);
      } else {
        return [...prev, id];
      }
    });
  }, []);

  const openReviewModal = useCallback(
    (itemId: number | string, itemName: string, orderId: string) => {
      setRating(5);
      setReviewText("");
      setReviewModal({ isOpen: true, itemId, itemName, orderId });
    },
    []
  );

  const submitReview = useCallback(async () => {
    if (!reviewModal.itemId || !reviewModal.orderId) return;

    setIsSubmitting(true);
    try {
      // If onSubmitReview prop is provided, use it (real API)
      // Pass itemId as order_item_id so backend knows which specific product to review
      if (onSubmitReview) {
        await onSubmitReview(
          reviewModal.orderId,
          rating,
          reviewText || undefined,
          String(reviewModal.itemId)
        );
      }

      // Update local state to show "Reviewed" status for THIS specific item only
      const updatedOrders = ordersState.map((order) => ({
        ...order,
        items: order.items.map((item) =>
          item.id === reviewModal.itemId ? { ...item, hasReview: true } : item
        ),
      }));

      setOrdersState(updatedOrders);
      setReviewModal({ isOpen: false, itemId: null, itemName: "", orderId: null });
    } catch (error) {
      logger.error(
        "Failed to submit review",
        error instanceof Error ? error : new Error(String(error))
      );
    } finally {
      setIsSubmitting(false);
    }
  }, [reviewModal.itemId, reviewModal.orderId, rating, reviewText, onSubmitReview, ordersState]);

  const filteredOrders = ordersState.filter((order) => {
    // Check expiration for pending orders
    const isExpired = order.deadline ? new Date(order.deadline) < new Date() : false;
    const isPendingExpired = order.rawStatus === "pending" && isExpired;
    const isExplicitlyExpired =
      order.rawStatus === "expired" || order.statusMessage?.includes("expired");

    // Always hide garbage orders: cancelled, expired pending (user never paid)
    // These clutter the UI and have no value for the user
    if (order.rawStatus === "cancelled" || isPendingExpired || isExplicitlyExpired) {
      return false;
    }

    if (activeTab === "all") {
      // Show all non-garbage orders
      return true;
    }

    // Active: orders in progress (pending payment, paid awaiting delivery, prepaid, partial)
    if (activeTab === "active") {
      return (
        order.rawStatus === "pending" || // Awaiting payment (not expired - checked above)
        order.rawStatus === "paid" || // Paid, awaiting delivery
        order.rawStatus === "prepaid" || // Paid, waiting for stock
        order.rawStatus === "partial"
      ); // Partially delivered
    }

    // Completed: delivered and refunded orders only
    if (activeTab === "log") {
      return order.rawStatus === "delivered" || order.rawStatus === "refunded";
    }
    return true;
  });

  // Empty state when no orders
  if (ordersState.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
      >
        <div className="max-w-6xl mx-auto">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-8 transition-colors"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Package size={64} className="text-gray-700 mb-6" />
            <h2 className="text-2xl font-bold text-white mb-2">
              {t("empty.orders").toUpperCase()}
            </h2>
            <p className="text-gray-500 font-mono text-sm max-w-md">{t("empty.ordersHint")}</p>
            <button
              onClick={onBack}
              className="mt-8 px-6 py-3 bg-pandora-cyan/10 border border-pandora-cyan text-pandora-cyan font-mono text-sm uppercase hover:bg-pandora-cyan/20 transition-colors"
            >
              {t("empty.browseCatalog")}
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
    >
      <div className="max-w-7xl mx-auto relative z-10">
        {/* === UNIFIED HEADER (Leaderboard Style) === */}
        <div className="mb-8 md:mb-16">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
            {t("orders.title").toUpperCase()}
          </h1>
          <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan tracking-widest uppercase">
            <Terminal size={12} />
            <span>{t("orders.subtitle")}</span>
          </div>
        </div>

        {/* --- TABS --- */}
        <div className="flex gap-8 mb-10 pl-2 overflow-x-auto">
          {[
            { id: "all", label: t("orders.tabs.all").toUpperCase() },
            { id: "active", label: t("orders.tabs.active").toUpperCase() },
            { id: "log", label: t("orders.tabs.completed").toUpperCase() },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className="relative pb-2 text-sm font-mono font-bold tracking-wider uppercase transition-colors whitespace-nowrap"
            >
              <span
                className={
                  activeTab === tab.id ? "text-pandora-cyan" : "text-gray-600 hover:text-gray-400"
                }
              >
                {tab.label}
              </span>
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeOrderTab"
                  className="absolute bottom-0 left-0 w-full h-0.5 bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                />
              )}
            </button>
          ))}
        </div>

        {/* --- ORDERS LIST (Native) --- */}
        <div className="space-y-8">
          {filteredOrders.map((order) => (
            <OrderCard
              key={order.id}
              order={order}
              revealedKeys={revealedKeys}
              copiedId={copiedId}
              onToggleReveal={toggleReveal}
              onCopy={handleCopy}
              onOpenReview={openReviewModal}
              onOpenSupport={onOpenSupport}
            />
          ))}
        </div>

        {/* Footer */}
        {onOpenSupport && (
          <div className="mt-16 border-t border-white/10 pt-8 text-center">
            <div
              onClick={() => onOpenSupport()}
              className="inline-flex flex-col items-center gap-2 group cursor-pointer"
            >
              <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center border border-white/10 group-hover:border-pandora-cyan group-hover:text-pandora-cyan transition-all">
                <Box size={18} />
              </div>
              <span className="text-[10px] font-mono text-gray-500 group-hover:text-white transition-colors">
                {t("orders.initSupport").toUpperCase()}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* === REVIEW MODAL === */}
      <OrderReviewModal
        isOpen={reviewModal.isOpen}
        itemId={reviewModal.itemId}
        itemName={reviewModal.itemName}
        orderId={reviewModal.orderId}
        rating={rating}
        reviewText={reviewText}
        isSubmitting={isSubmitting}
        onClose={() => setReviewModal({ ...reviewModal, isOpen: false })}
        onRatingChange={setRating}
        onTextChange={setReviewText}
        onSubmit={submitReview}
      />
    </motion.div>
  );
};

export default Orders;
