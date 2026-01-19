/**
 * OrderCard Component
 *
 * Displays a complete order card with header, status banners, and items.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Package,
  RefreshCw,
  Shield,
} from "lucide-react";
import type React from "react";
import { memo, useState } from "react";
import { useOrdersTyped } from "../../hooks/api/useOrdersApi";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";
import OrderItem, { type OrderItemData } from "./OrderItem";
import OrderStatusBadge from "./OrderStatusBadge";
import { PaymentCountdown } from "./PaymentCountdown";

export interface RefundContext {
  orderId: string;
  itemId?: string; // Specific item ID if reporting issue for a single item
  orderTotal: number;
  productNames: string[];
  reason?: string;
}

type RawOrderStatus =
  | "pending"
  | "prepaid"
  | "paid"
  | "partial"
  | "delivered"
  | "cancelled"
  | "refunded"
  | "expired"
  | "failed";

export interface OrderData {
  id: string;
  displayId?: string;
  date: string;
  total: number;
  currency?: string;
  status: "paid" | "processing" | "refunded";
  items: OrderItemData[];
  payment_url?: string | null;
  payment_id?: string | null; // Invoice ID for checking payment status
  payment_gateway?: string | null; // Gateway name
  deadline?: string | null; // Payment deadline for pending orders
  rawStatus?: RawOrderStatus;
  paymentConfirmed?: boolean;
  statusMessage?: string;
  canCancel?: boolean;
  canRequestRefund?: boolean;
}

interface OrderCardProps {
  order: OrderData;
  revealedKeys: (string | number)[];
  copiedId: string | number | null;
  onToggleReveal: (id: string | number) => void;
  onCopy: (text: string, id: string | number) => void;
  onOpenReview: (itemId: string | number, itemName: string, orderId: string) => void;
  onOpenSupport?: (context?: RefundContext) => void;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

const OrderCard: React.FC<OrderCardProps> = ({
  order,
  revealedKeys,
  copiedId,
  onToggleReveal,
  onCopy,
  onOpenReview,
  onOpenSupport,
  isExpanded: propIsExpanded,
  onToggleExpand,
}) => {
  const { t } = useLocale();
  const { verifyPayment } = useOrdersTyped();
  const [isCheckingPayment, setIsCheckingPayment] = useState(false);
  const [paymentCheckResult, setPaymentCheckResult] = useState<string | null>(null);
  const [internalExpanded, setInternalExpanded] = useState(true);

  // Use prop if provided, otherwise use internal state
  const isExpanded = propIsExpanded === undefined ? internalExpanded : propIsExpanded;
  const handleToggleExpand = onToggleExpand || (() => setInternalExpanded((prev) => !prev));

  const handleCheckPayment = async () => {
    if (!(order.payment_id && order.payment_gateway)) {
      setPaymentCheckResult(t("orders.paymentNotChecked"));
      return;
    }

    setIsCheckingPayment(true);
    setPaymentCheckResult(null);

    try {
      const result = await verifyPayment(order.id);
      if (result) {
        if (result.status === "processed" || result.invoice_state === "payed") {
          setPaymentCheckResult("✅ Оплата подтверждена! Обновление статуса...");
          // Reload page after 2 seconds to show updated status
          setTimeout(() => {
            globalThis.location.reload();
          }, 2000);
        } else {
          setPaymentCheckResult(
            `Статус: ${result.invoice_state || result.status}. ${result.message || ""}`
          );
        }
      } else {
        setPaymentCheckResult("Ошибка проверки оплаты");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Ошибка при проверке оплаты";
      setPaymentCheckResult(errorMessage);
    } finally {
      setIsCheckingPayment(false);
    }
  };

  // Check if payment deadline has expired
  const isPaymentExpired = order.deadline ? new Date(order.deadline) < new Date() : false;

  return (
    <div className="group relative">
      {/* Connecting Line */}
      <div className="absolute top-0 bottom-0 -left-3 w-px bg-white/5 transition-colors group-hover:bg-white/10" />

      {/* Order Card */}
      <div className="relative overflow-hidden border border-white/10 bg-[#080808] transition-all hover:border-white/20">
        {/* Card Header */}
        <button
          className="flex w-full cursor-pointer items-center justify-between border-white/5 border-b bg-white/5 p-3 text-left transition-colors hover:bg-white/10"
          onClick={handleToggleExpand}
          type="button"
        >
          <div className="flex flex-1 items-center gap-4">
            <div
              className="rounded p-1 transition-colors hover:bg-white/10"
              title={isExpanded ? t("orders.collapseItems") : t("orders.expandItems")}
            >
              {isExpanded ? (
                <ChevronUp className="text-gray-400 hover:text-pandora-cyan" size={16} />
              ) : (
                <ChevronDown className="text-gray-400 hover:text-pandora-cyan" size={16} />
              )}
            </div>
            <div className="flex flex-1 items-center gap-4">
              <span className="font-mono text-pandora-cyan text-xs tracking-wider">
                ID: {order.displayId || order.id}
              </span>
              <span className="hidden font-mono text-[10px] text-gray-600 uppercase sm:inline">
                {"// "}
                {order.date}
              </span>
              {!isExpanded && (
                <span className="font-mono text-[10px] text-gray-500">
                  ({order.items.length}{" "}
                  {order.items.length === 1 ? t("orders.itemSingular") : t("orders.itemPlural")})
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <OrderStatusBadge rawStatus={order.rawStatus} status={order.status} />
            <span className="font-bold font-display text-white">
              {formatPrice(order.total, order.currency || "USD")}
            </span>
          </div>
        </button>

        {/* Status Explanation Banner */}
        {order.statusMessage && order.rawStatus !== "prepaid" && (
          <div
            className={`border-b px-4 py-2 font-mono text-[10px] ${
              order.paymentConfirmed
                ? "border-green-500/20 bg-green-500/5 text-green-400"
                : "border-orange-500/20 bg-orange-500/5 text-orange-400"
            }`}
          >
            <div className="flex items-center gap-2">
              {order.paymentConfirmed ? <Check size={12} /> : <Clock size={12} />}
              {order.rawStatus
                ? t(`orders.statusMessages.${order.rawStatus}`)
                : order.statusMessage}
            </div>
          </div>
        )}

        {/* Payment Button - ONLY for unpaid orders */}
        {order.rawStatus === "pending" && order.payment_url && (
          <div className="border-orange-500/20 border-b bg-orange-500/10 p-4">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="font-mono text-[10px] text-orange-400">
                  <span className="flex items-center gap-2">
                    <AlertTriangle size={12} />
                    {t("orders.paymentRequired")}
                  </span>
                </div>
                <button
                  className={`px-4 py-2 font-bold font-mono text-xs uppercase transition-colors ${
                    isPaymentExpired
                      ? "cursor-not-allowed border border-white/10 bg-gray-700/50 text-gray-400"
                      : "bg-pandora-cyan text-black hover:bg-pandora-cyan/80"
                  }`}
                  disabled={isPaymentExpired}
                  onClick={() => {
                    if (isPaymentExpired || !order.payment_url) return;
                    globalThis.location.href = order.payment_url;
                  }}
                  type="button"
                >
                  {isPaymentExpired ? t("orders.paymentExpired") : t("orders.payNow")}
                </button>
              </div>

              {/* Payment Status Info */}
              {(order.payment_id || order.payment_gateway) && (
                <div className="space-y-1 border-white/5 border-t pt-2 font-mono text-[10px] text-gray-400">
                  {order.payment_id && (
                    <div className="flex items-center justify-between">
                      <span>{t("orders.invoiceId")}:</span>
                      <span className="font-mono text-pandora-cyan">
                        {order.payment_id.substring(0, 12)}...
                      </span>
                    </div>
                  )}
                  {order.payment_gateway && (
                    <div className="flex items-center justify-between">
                      <span>{t("orders.gateway")}:</span>
                      <span className="text-gray-300 uppercase">{order.payment_gateway}</span>
                    </div>
                  )}
                  {isPaymentExpired && (
                    <div className="flex items-center gap-2 text-red-400">
                      <AlertTriangle size={10} />
                      <span>{t("orders.paymentExpired")}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Check Payment Button */}
              {order.payment_id && order.payment_gateway === "crystalpay" && (
                <div className="flex flex-col gap-2">
                  <button
                    className="flex items-center justify-center gap-2 border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-[10px] text-gray-300 uppercase transition-colors hover:bg-white/10 disabled:opacity-50"
                    disabled={isCheckingPayment}
                    onClick={handleCheckPayment}
                    type="button"
                  >
                    {isCheckingPayment ? (
                      <>
                        <RefreshCw className="animate-spin" size={10} />
                        {t("orders.checkingPayment")}
                      </>
                    ) : (
                      <>
                        <RefreshCw size={10} />
                        {t("orders.checkPayment")}
                      </>
                    )}
                  </button>
                  {paymentCheckResult && (
                    <div className="rounded bg-black/20 px-2 py-1 font-mono text-[9px] text-gray-400">
                      {paymentCheckResult}
                    </div>
                  )}
                </div>
              )}

              {order.deadline && <PaymentCountdown deadline={order.deadline} />}
            </div>
          </div>
        )}

        {/* Waiting for Stock Banner - for prepaid orders */}
        {order.rawStatus === "prepaid" && (
          <div className="border-purple-500/20 border-b bg-purple-500/10 p-4">
            <div className="font-mono text-[11px] text-purple-400">
              <div className="mb-2 flex items-center gap-2">
                <Check className="text-green-400" size={12} />
                <span className="text-green-400">{t("orders.paymentConfirmed")}</span>
              </div>
              <div className="mb-2 flex items-center gap-2 text-purple-300">
                <Package size={12} />
                {t("orders.waitingStockDesc")}
              </div>
              <div className="flex items-center gap-2 text-[10px] text-gray-500">
                <Shield size={10} />
                {t("orders.autoRefund")}
              </div>
            </div>
          </div>
        )}

        {/* Warranty Info Banner - shows if any item has active warranty */}
        {order.rawStatus === "delivered" && order.items.some((item) => item.canRequestRefund) && (
          <div className="border-green-500/20 border-b bg-green-500/5 p-4">
            <div className="font-mono text-[11px] text-green-400">
              <div className="flex items-center gap-2">
                <Shield size={12} />
                {t("orders.warrantyActive")}
              </div>
              <div className="mt-1 text-[10px] text-gray-500">{t("orders.reportIssueHint")}</div>
            </div>
          </div>
        )}

        {/* Items Content - Collapsible */}
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              animate={{ height: "auto", opacity: 1 }}
              className="overflow-hidden"
              exit={{ height: 0, opacity: 0 }}
              initial={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
            >
              <div className="space-y-6 p-5">
                {order.items.map((item) => (
                  <OrderItem
                    copiedId={copiedId}
                    item={item}
                    key={item.id}
                    onCopy={onCopy}
                    onOpenReview={onOpenReview}
                    onOpenSupport={
                      onOpenSupport
                        ? (context) => {
                            // Fill in orderTotal from order if not provided
                            if (!onOpenSupport) return; // Double check
                            const finalContext = {
                              ...context,
                              orderTotal: context.orderTotal || order.total,
                            };
                            onOpenSupport(finalContext);
                          }
                        : undefined
                    }
                    onToggleReveal={onToggleReveal}
                    orderId={order.id}
                    revealedKeys={revealedKeys}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Decorative Corner Overlays */}
        <div className="absolute top-0 right-0 h-2 w-2 border-pandora-cyan border-t border-r opacity-50" />
        <div className="absolute bottom-0 left-0 h-2 w-2 border-pandora-cyan border-b border-l opacity-50" />
      </div>
    </div>
  );
};

export default memo(OrderCard);
