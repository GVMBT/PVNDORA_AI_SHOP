/**
 * OrderItem Component
 *
 * Displays a single item within an order with its status, credentials, and actions.
 */

import {
  Activity,
  AlertTriangle,
  Check,
  Clock,
  Copy,
  Eye,
  EyeOff,
  MessageSquare,
  Timer,
} from "lucide-react";
import React, { memo, useEffect, useState } from "react";
import { useLocale } from "../../hooks/useLocale";
import { randomChar } from "../../utils/random";

/**
 * Hook to calculate countdown from deadline
 */
function useCountdown(deadline: string | null | undefined): {
  hours: number;
  minutes: number;
  seconds: number;
  isExpired: boolean;
  formatted: string;
} {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!deadline) return;

    const timer = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(timer);
  }, [deadline]);

  if (!deadline) {
    return { hours: 0, minutes: 0, seconds: 0, isExpired: true, formatted: "--:--:--" };
  }

  const target = new Date(deadline).getTime();
  const diff = target - now;

  if (diff <= 0) {
    return { hours: 0, minutes: 0, seconds: 0, isExpired: true, formatted: "00:00:00" };
  }

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  const pad = (n: number) => n.toString().padStart(2, "0");
  const formatted = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

  return { hours, minutes, seconds, isExpired: false, formatted };
}

export interface OrderItemData {
  id: string | number;
  name: string;
  type: "instant" | "preorder";
  status: "delivered" | "waiting" | "cancelled";
  credentials?: string | null;
  expiry?: string | null;
  hasReview: boolean;
  estimatedDelivery?: string | null;
  progress?: number | null;
  deadline?: string | null;
  deadlineRaw?: string | null; // ISO date string for countdown calculation
  reason?: string | null;
  orderRawStatus?:
    | "pending"
    | "paid"
    | "prepaid"
    | "partial"
    | "delivered"
    | "cancelled"
    | "refunded";
  deliveredAt?: string | null;
  canRequestRefund?: boolean;
  warrantyUntil?: string | null;
}

interface DecryptTextProps {
  text: string;
  revealed: boolean;
}

// Decrypt animation component
// Preserves newlines (\n) during animation for multi-line credentials
const DecryptText: React.FC<DecryptTextProps> = ({ text, revealed }) => {
  // Mask all chars EXCEPT newlines
  const maskChar = (char: string) => (char === "\n" ? "\n" : "•");
  const [display, setDisplay] = React.useState(() => text.split("").map(maskChar).join(""));

  React.useEffect(() => {
    if (!revealed) {
      // Hide: replace all chars with • except newlines
      setDisplay(text.split("").map(maskChar).join(""));
      return;
    }

    let iterations = 0;
    let rafId: number | null = null;
    let lastTime = performance.now();
    const targetInterval = 30;

    const animate = (currentTime: number) => {
      const delta = currentTime - lastTime;
      if (delta >= targetInterval) {
        setDisplay(
          text
            .split("")
            .map((char, index) => {
              // Preserve newlines during animation
              if (char === "\n") return "\n";
              if (index < iterations) return char;
              return randomChar("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*");
            })
            .join("")
        );

        if (iterations >= text.length) {
          if (rafId) cancelAnimationFrame(rafId);
          return;
        }
        iterations++;
        lastTime = currentTime;
      }
      rafId = requestAnimationFrame(animate);
    };

    rafId = requestAnimationFrame(animate);

    return () => {
      if (rafId) cancelAnimationFrame(rafId);
    };
  }, [revealed, text]);

  return <span className="font-mono whitespace-pre-wrap">{display}</span>;
};

interface OrderItemProps {
  item: OrderItemData;
  orderId: string;
  revealedKeys: (string | number)[];
  copiedId: string | number | null;
  onToggleReveal: (id: string | number) => void;
  onCopy: (text: string, id: string | number) => void;
  onOpenReview: (itemId: string | number, itemName: string, orderId: string) => void;
  onOpenSupport?: (context?: {
    orderId: string;
    itemId?: string;
    orderTotal: number;
    productNames: string[];
    reason?: string;
  }) => void;
}

const OrderItem: React.FC<OrderItemProps> = ({
  item,
  orderId,
  revealedKeys,
  copiedId,
  onToggleReveal,
  onCopy,
  onOpenReview,
  onOpenSupport,
}) => {
  const { t } = useLocale();
  const isRevealed = revealedKeys.includes(item.id);

  // Countdown timer for prepaid items
  const countdown = useCountdown(item.deadlineRaw);

  return (
    <div className="relative pl-4 border-l-2 border-white/10 group-hover:border-pandora-cyan/30 transition-colors">
      {/* Item Header */}
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-bold text-white text-sm tracking-wide">{item.name}</h3>

        <div className="text-[10px] font-mono">
          {item.status === "delivered" && (
            <span className="text-green-500 flex items-center gap-1">
              <Check size={10} /> {t("orders.itemStatus.delivered")}
            </span>
          )}
          {item.status === "waiting" && (
            <>
              {/* Show QUEUED only if payment is confirmed */}
              {item.orderRawStatus && item.orderRawStatus !== "pending" ? (
                <span className="text-orange-400 flex items-center gap-1">
                  <Clock size={10} /> {t("orders.itemStatus.queued")}
                </span>
              ) : (
                <span className="text-gray-500 flex items-center gap-1">
                  <Clock size={10} /> {t("orders.itemStatus.awaitingPayment")}
                </span>
              )}
            </>
          )}
          {item.status === "cancelled" && (
            <span className="text-red-500 flex items-center gap-1">
              <AlertTriangle size={10} /> {t("orders.itemStatus.cancelled")}
            </span>
          )}
        </div>
      </div>

      {/* === DELIVERED: Credentials & Actions === */}
      {item.status === "delivered" && (
        <div className="space-y-3">
          {/* Credentials Box */}
          {item.credentials && (
            <div className="bg-black border border-white/10 border-dashed p-3 relative group/key">
              <div className="text-[10px] text-gray-500 font-mono mb-2 flex justify-between items-center border-b border-white/5 pb-2">
                <span>{t("orders.item.accessKeyEncrypted")}</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onToggleReveal(item.id)}
                    className="text-gray-500 hover:text-white transition-colors"
                  >
                    {isRevealed ? <EyeOff size={12} /> : <Eye size={12} />}
                  </button>
                  {item.expiry && (
                    <span className="text-gray-600">
                      {t("orders.item.expires")}: {item.expiry}
                    </span>
                  )}
                </div>
              </div>

              {/* Key Content */}
              <div className="flex justify-between items-center mt-2 gap-2">
                <div className="font-mono text-xs sm:text-sm text-pandora-cyan tracking-wider overflow-hidden min-w-0 flex-1">
                  <div className="break-all overflow-x-auto scrollbar-hide max-w-full whitespace-pre-wrap">
                    <DecryptText text={item.credentials} revealed={isRevealed} />
                  </div>
                </div>
                <button
                  onClick={() => onCopy(item.credentials!, item.id)}
                  className="p-1.5 bg-white/5 hover:bg-pandora-cyan hover:text-black transition-colors rounded-sm flex-shrink-0"
                  title="Copy to Clipboard"
                >
                  {copiedId === item.id ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
            </div>
          )}

          {/* Actions Row: Review + Report Issue (Only for delivered items) */}
          <div className="flex justify-end items-center gap-2 pt-2">
            {/* Report Issue Button (if within warranty) */}
            {item.status === "delivered" && item.canRequestRefund && onOpenSupport && (
              <button
                onClick={() =>
                  onOpenSupport({
                    orderId: orderId,
                    itemId: String(item.id),
                    orderTotal: 0, // Will be filled by parent
                    productNames: [item.name],
                    reason: `WARRANTY_CLAIM: Проблема с аккаунтом "${item.name}"`,
                  })
                }
                className="flex items-center gap-2 text-[10px] font-bold font-mono text-green-400 border border-green-500/30 px-3 py-1.5 hover:bg-green-500/20 transition-all"
              >
                <AlertTriangle size={12} />
                {t("orders.item.reportIssue")}
              </button>
            )}

            {/* Review Action */}
            {item.hasReview ? (
              <div className="flex items-center gap-2 text-[10px] font-mono text-gray-500 border border-white/5 px-3 py-1.5 rounded-sm select-none opacity-60">
                <Check size={12} className="text-pandora-cyan" />
                {t("orders.item.feedbackLogged")}
              </div>
            ) : (
              <button
                onClick={() => onOpenReview(item.id, item.name, orderId)}
                className="flex items-center gap-2 text-[10px] font-bold font-mono text-pandora-cyan border border-pandora-cyan/30 px-3 py-1.5 hover:bg-pandora-cyan hover:text-black transition-all"
              >
                <MessageSquare size={12} />
                {t("orders.item.initializeReview")}
              </button>
            )}
          </div>
        </div>
      )}

      {/* === WAITING: Pre-order or Processing === */}
      {item.status === "waiting" && (
        <div className="mt-2 bg-[#0c0c0c] border border-orange-500/20 p-3">
          {/* Show PROVISIONING only if payment is confirmed */}
          {item.orderRawStatus && item.orderRawStatus !== "pending" ? (
            <>
              <div className="flex justify-between text-[10px] font-mono text-orange-400 mb-1">
                <span className="flex items-center gap-1">
                  <Activity size={10} /> {t("orders.itemStatus.provisioning")}...
                </span>
                <span>
                  {t("orders.itemStatus.estimatedTime")}: {item.estimatedDelivery}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-1 bg-gray-800 mt-2 mb-2 relative overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-orange-500 shadow-[0_0_10px_orange]"
                  style={{ width: `${item.progress || 0}%` }}
                />
                <div className="absolute top-0 left-0 h-full w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-pulse" />
              </div>

              {/* Deadline with Countdown */}
              <div className="border-t border-white/5 pt-2 mt-2 flex justify-between items-center">
                <p className="text-[10px] text-gray-500 font-mono">
                  &gt; {t("orders.item.deadline")}: {item.deadline}
                </p>
                {item.deadlineRaw && !countdown.isExpired && (
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded">
                    <Timer size={10} className="animate-pulse" />
                    <span>{countdown.formatted}</span>
                  </div>
                )}
                {countdown.isExpired && item.deadlineRaw && (
                  <div className="flex items-center gap-1 text-[10px] font-mono text-red-400">
                    <AlertTriangle size={10} />
                    <span>{t("orders.itemStatus.deadlineExpired")}</span>
                  </div>
                )}
              </div>
            </>
          ) : (
            /* For unpaid orders, show payment deadline only */
            item.deadline && (
              <p className="text-[10px] text-gray-500 font-mono">
                &gt; {t("orders.item.deadline")}: {item.deadline}
              </p>
            )
          )}
        </div>
      )}

      {/* === REFUNDED === */}
      {item.status === "cancelled" && (
        <div className="mt-2 bg-red-900/5 border border-red-500/20 p-2 font-mono text-[10px] text-red-400">
          &gt; {item.reason}
        </div>
      )}
    </div>
  );
};

export default memo(OrderItem);
