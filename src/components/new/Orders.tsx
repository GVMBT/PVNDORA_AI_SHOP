import { motion } from "framer-motion";
import { ArrowLeft, Box, Package, Terminal } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useClipboard } from "../../hooks/useClipboard";
import { useLocale } from "../../hooks/useLocale";
import { useTimeoutState } from "../../hooks/useTimeoutState";
import { logger } from "../../utils/logger";
import OrderCard, { type OrderData, type RefundContext } from "./OrderCard";
import OrderReviewModal from "./OrderReviewModal";

// Re-export types for backward compatibility
export type { OrderData, RefundContext } from "./OrderCard";
export type { OrderItemData } from "./OrderItem";

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

type TabId = "all" | "active" | "log";

const Orders: React.FC<OrdersProps> = ({
  orders: propOrders,
  onBack,
  onOpenSupport,
  onSubmitReview,
}) => {
  const { t, tEn } = useLocale();
  // Use provided orders - NO MOCK fallback
  const ordersData = propOrders || [];
  const [activeTab, setActiveTab] = useState<"all" | "active" | "log">("all");
  const [copiedId, setCopiedId] = useTimeoutState<number | string | null>(null);
  const [revealedKeys, setRevealedKeys] = useState<(number | string)[]>([]);
  // Note: expandedOrders state removed - expansion is now handled per-order by OrderCard

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
      }
      return [...prev, id];
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
    if (!(reviewModal.itemId && reviewModal.orderId)) return;

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
        animate={{ opacity: 1 }}
        className="relative min-h-screen px-4 pt-20 pb-32 text-white md:px-8 md:pt-24 md:pl-28"
        exit={{ opacity: 0 }}
        initial={{ opacity: 0 }}
      >
        <div className="mx-auto max-w-6xl">
          <button
            className="mb-8 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
            onClick={onBack}
            type="button"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Package className="mb-6 text-gray-700" size={64} />
            <h2 className="mb-2 font-bold text-2xl text-white">
              {t("empty.orders").toUpperCase()}
            </h2>
            <p className="max-w-md font-mono text-gray-500 text-sm">{t("empty.ordersHint")}</p>
            <button
              className="mt-8 border border-pandora-cyan bg-pandora-cyan/10 px-6 py-3 font-mono text-pandora-cyan text-sm uppercase transition-colors hover:bg-pandora-cyan/20"
              onClick={onBack}
              type="button"
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
      animate={{ opacity: 1 }}
      className="relative min-h-screen px-4 pt-20 pb-32 text-white md:px-8 md:pt-24 md:pl-28"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
    >
      <div className="relative z-10 mx-auto max-w-7xl">
        {/* === UNIFIED HEADER (Leaderboard Style) === */}
        <div className="mb-8 md:mb-16">
          <button
            className="mb-4 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
            onClick={onBack}
            type="button"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <h1 className="mb-4 font-black font-display text-3xl text-white uppercase leading-[0.9] tracking-tighter sm:text-4xl md:text-6xl">
            {tEn("orders.pageTitle")}
          </h1>
          <div className="flex items-center gap-2 font-mono text-[10px] text-pandora-cyan uppercase tracking-widest">
            <Terminal size={12} />
            <span>{t("orders.subtitle")}</span>
          </div>
        </div>

        {/* --- TABS --- */}
        <div className="mb-10 flex gap-8 overflow-x-auto pl-2">
          {[
            { id: "all", label: t("orders.tabs.all").toUpperCase() },
            { id: "active", label: t("orders.tabs.active").toUpperCase() },
            { id: "log", label: t("orders.tabs.completed").toUpperCase() },
          ].map((tab) => (
            <button
              className="relative whitespace-nowrap pb-2 font-bold font-mono text-sm uppercase tracking-wider transition-colors"
              key={tab.id}
              onClick={() => setActiveTab(tab.id as TabId)}
              type="button"
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
                  className="absolute bottom-0 left-0 h-0.5 w-full bg-pandora-cyan shadow-[0_0_10px_#00FFFF]"
                  layoutId="activeOrderTab"
                />
              )}
            </button>
          ))}
        </div>

        {/* --- ORDERS LIST (Native) --- */}
        <div className="space-y-8">
          {filteredOrders.map((order) => (
            <OrderCard
              copiedId={copiedId}
              key={order.id}
              onCopy={handleCopy}
              onOpenReview={openReviewModal}
              onOpenSupport={onOpenSupport}
              onToggleReveal={toggleReveal}
              order={order}
              revealedKeys={revealedKeys}
            />
          ))}
        </div>

        {/* Footer */}
        {onOpenSupport && (
          <div className="mt-16 border-white/10 border-t pt-8 text-center">
            <button
              className="group inline-flex cursor-pointer flex-col items-center gap-2 border-0 bg-transparent"
              onClick={() => onOpenSupport()}
              type="button"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/5 transition-all group-hover:border-pandora-cyan group-hover:text-pandora-cyan">
                <Box size={18} />
              </div>
              <span className="font-mono text-[10px] text-gray-500 transition-colors group-hover:text-white">
                {t("orders.initSupport").toUpperCase()}
              </span>
            </button>
          </div>
        )}
      </div>

      {/* === REVIEW MODAL === */}
      <OrderReviewModal
        isOpen={reviewModal.isOpen}
        isSubmitting={isSubmitting}
        itemId={reviewModal.itemId}
        itemName={reviewModal.itemName}
        onClose={() => setReviewModal({ ...reviewModal, isOpen: false })}
        onRatingChange={setRating}
        onSubmit={submitReview}
        onTextChange={setReviewText}
        orderId={reviewModal.orderId}
        rating={rating}
        reviewText={reviewText}
      />
    </motion.div>
  );
};

export default Orders;
