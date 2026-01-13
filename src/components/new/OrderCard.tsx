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
    if (!order.payment_id || !order.payment_gateway) {
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
      setPaymentCheckResult("Ошибка при проверке оплаты");
    } finally {
      setIsCheckingPayment(false);
    }
  };

  // Check if payment deadline has expired
  const isPaymentExpired = order.deadline ? new Date(order.deadline) < new Date() : false;

  return (
    <div className="relative group">
      {/* Connecting Line */}
      <div className="absolute -left-3 top-0 bottom-0 w-px bg-white/5 group-hover:bg-white/10 transition-colors" />

      {/* Order Card */}
      <div className="bg-[#080808] border border-white/10 hover:border-white/20 transition-all relative overflow-hidden">
        {/* Card Header */}
        <button
          type="button"
          className="bg-white/5 p-3 flex justify-between items-center border-b border-white/5 cursor-pointer hover:bg-white/10 transition-colors w-full text-left"
          onClick={handleToggleExpand}
        >
          <div className="flex items-center gap-4 flex-1">
            <div
              className="p-1 hover:bg-white/10 rounded transition-colors"
              title={isExpanded ? t("orders.collapseItems") : t("orders.expandItems")}
            >
              {isExpanded ? (
                <ChevronUp size={16} className="text-gray-400 hover:text-pandora-cyan" />
              ) : (
                <ChevronDown size={16} className="text-gray-400 hover:text-pandora-cyan" />
              )}
            </div>
            <div className="flex items-center gap-4 flex-1">
              <span className="font-mono text-xs text-pandora-cyan tracking-wider">
                ID: {order.displayId || order.id}
              </span>
              <span className="hidden sm:inline text-[10px] font-mono text-gray-600 uppercase">
                // {order.date}
              </span>
              {!isExpanded && (
                <span className="text-[10px] font-mono text-gray-500">
                  ({order.items.length}{" "}
                  {order.items.length === 1 ? t("orders.itemSingular") : t("orders.itemPlural")})
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <OrderStatusBadge rawStatus={order.rawStatus} status={order.status} />
            <span className="font-display font-bold text-white">
              {formatPrice(order.total, order.currency || "USD")}
            </span>
          </div>
        </button>

        {/* Status Explanation Banner */}
        {order.statusMessage && order.rawStatus !== "prepaid" && (
          <div
            className={`px-4 py-2 text-[10px] font-mono border-b ${
              order.paymentConfirmed
                ? "bg-green-500/5 border-green-500/20 text-green-400"
                : "bg-orange-500/5 border-orange-500/20 text-orange-400"
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
          <div className="p-4 bg-orange-500/10 border-b border-orange-500/20">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="text-[10px] font-mono text-orange-400">
                  <span className="flex items-center gap-2">
                    <AlertTriangle size={12} />
                    {t("orders.paymentRequired")}
                  </span>
                </div>
                <button
                  disabled={isPaymentExpired}
                  onClick={() => {
                    if (isPaymentExpired) return;
                    globalThis.location.href = order.payment_url!;
                  }}
                  className={`px-4 py-2 font-mono text-xs font-bold uppercase transition-colors ${
                    isPaymentExpired
                      ? "bg-gray-700/50 text-gray-400 cursor-not-allowed border border-white/10"
                      : "bg-pandora-cyan text-black hover:bg-pandora-cyan/80"
                  }`}
                >
                  {isPaymentExpired ? t("orders.paymentExpired") : t("orders.payNow")}
                </button>
              </div>

              {/* Payment Status Info */}
              {(order.payment_id || order.payment_gateway) && (
                <div className="text-[10px] font-mono text-gray-400 space-y-1 border-t border-white/5 pt-2">
                  {order.payment_id && (
                    <div className="flex items-center justify-between">
                      <span>{t("orders.invoiceId")}:</span>
                      <span className="text-pandora-cyan font-mono">
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
                    onClick={handleCheckPayment}
                    disabled={isCheckingPayment}
                    className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 text-[10px] font-mono text-gray-300 uppercase flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  >
                    {isCheckingPayment ? (
                      <>
                        <RefreshCw size={10} className="animate-spin" />
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
                    <div className="text-[9px] font-mono text-gray-400 px-2 py-1 bg-black/20 rounded">
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
          <div className="p-4 bg-purple-500/10 border-b border-purple-500/20">
            <div className="text-[11px] font-mono text-purple-400">
              <div className="flex items-center gap-2 mb-2">
                <Check size={12} className="text-green-400" />
                <span className="text-green-400">{t("orders.paymentConfirmed")}</span>
              </div>
              <div className="flex items-center gap-2 text-purple-300 mb-2">
                <Package size={12} />
                {t("orders.waitingStockDesc")}
              </div>
              <div className="flex items-center gap-2 text-gray-500 text-[10px]">
                <Shield size={10} />
                {t("orders.autoRefund")}
              </div>
            </div>
          </div>
        )}

        {/* Warranty Info Banner - shows if any item has active warranty */}
        {order.rawStatus === "delivered" && order.items.some((item) => item.canRequestRefund) && (
          <div className="p-4 bg-green-500/5 border-b border-green-500/20">
            <div className="text-[11px] font-mono text-green-400">
              <div className="flex items-center gap-2">
                <Shield size={12} />
                {t("orders.warrantyActive")}
              </div>
              <div className="text-[10px] text-gray-500 mt-1">{t("orders.reportIssueHint")}</div>
            </div>
          </div>
        )}

        {/* Items Content - Collapsible */}
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="p-5 space-y-6">
                {order.items.map((item) => (
                  <OrderItem
                    key={item.id}
                    item={item}
                    orderId={order.id}
                    revealedKeys={revealedKeys}
                    copiedId={copiedId}
                    onToggleReveal={onToggleReveal}
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
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Decorative Corner Overlays */}
        <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-pandora-cyan opacity-50" />
        <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-pandora-cyan opacity-50" />
      </div>
    </div>
  );
};

export default memo(OrderCard);
