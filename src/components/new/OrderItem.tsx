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

// Helper function to mask characters (preserve newlines)
const maskTextChar = (char: string): string => {
  if (char === "\n") return "\n";
  return "•";
};

// Decrypt animation component
// Preserves newlines (\n) during animation for multi-line credentials
const DecryptText: React.FC<DecryptTextProps> = ({ text, revealed }) => {
  const [display, setDisplay] = React.useState(() => text.split("").map(maskTextChar).join(""));

  React.useEffect(() => {
    if (!revealed) {
      // Hide: replace all chars with • except newlines
      setDisplay(text.split("").map(maskTextChar).join(""));
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

  return <span className="whitespace-pre-wrap font-mono">{display}</span>;
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
    <div className="relative border-white/10 border-l-2 pl-4 transition-colors group-hover:border-pandora-cyan/30">
      {/* Item Header */}
      <div className="mb-3 flex items-start justify-between">
        <h3 className="font-bold text-sm text-white tracking-wide">{item.name}</h3>

        <div className="font-mono text-[10px]">
          {item.status === "delivered" && (
            <span className="flex items-center gap-1 text-green-500">
              <Check size={10} /> {t("orders.itemStatus.delivered")}
            </span>
          )}
          {item.status === "waiting" && (
            <>
              {/* Show QUEUED only if payment is confirmed */}
              {item.orderRawStatus && item.orderRawStatus !== "pending" ? (
                <span className="flex items-center gap-1 text-orange-400">
                  <Clock size={10} /> {t("orders.itemStatus.queued")}
                </span>
              ) : (
                <span className="flex items-center gap-1 text-gray-500">
                  <Clock size={10} /> {t("orders.itemStatus.awaitingPayment")}
                </span>
              )}
            </>
          )}
          {item.status === "cancelled" && (
            <span className="flex items-center gap-1 text-red-500">
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
            <div className="group/key relative border border-white/10 border-dashed bg-black p-3">
              <div className="mb-2 flex items-center justify-between border-white/5 border-b pb-2 font-mono text-[10px] text-gray-500">
                <span>{t("orders.item.accessKeyEncrypted")}</span>
                <div className="flex items-center gap-2">
                  <button
                    className="text-gray-500 transition-colors hover:text-white"
                    onClick={() => onToggleReveal(item.id)}
                    type="button"
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
              <div className="mt-2 flex items-center justify-between gap-2">
                <div className="min-w-0 flex-1 overflow-hidden font-mono text-pandora-cyan text-xs tracking-wider sm:text-sm">
                  <div className="scrollbar-hide max-w-full overflow-x-auto whitespace-pre-wrap break-all">
                    <DecryptText revealed={isRevealed} text={item.credentials} />
                  </div>
                </div>
                <button
                  className="flex-shrink-0 rounded-sm bg-white/5 p-1.5 transition-colors hover:bg-pandora-cyan hover:text-black"
                  onClick={() => onCopy(item.credentials ?? "", item.id)}
                  title="Copy to Clipboard"
                  type="button"
                >
                  {copiedId === item.id ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
            </div>
          )}

          {/* Actions Row: Review + Report Issue (Only for delivered items) */}
          <div className="flex items-center justify-end gap-2 pt-2">
            {/* Report Issue Button (if within warranty) */}
            {item.status === "delivered" && item.canRequestRefund && onOpenSupport && (
              <button
                className="flex items-center gap-2 border border-green-500/30 px-3 py-1.5 font-bold font-mono text-[10px] text-green-400 transition-all hover:bg-green-500/20"
                onClick={() =>
                  onOpenSupport({
                    orderId,
                    itemId: String(item.id),
                    orderTotal: 0, // Will be filled by parent
                    productNames: [item.name],
                    reason: `WARRANTY_CLAIM: Проблема с аккаунтом "${item.name}"`,
                  })
                }
                type="button"
              >
                <AlertTriangle size={12} />
                {t("orders.item.reportIssue")}
              </button>
            )}

            {/* Review Action */}
            {item.hasReview ? (
              <div className="flex select-none items-center gap-2 rounded-sm border border-white/5 px-3 py-1.5 font-mono text-[10px] text-gray-500 opacity-60">
                <Check className="text-pandora-cyan" size={12} />
                {t("orders.item.feedbackLogged")}
              </div>
            ) : (
              <button
                className="flex items-center gap-2 border border-pandora-cyan/30 px-3 py-1.5 font-bold font-mono text-[10px] text-pandora-cyan transition-all hover:bg-pandora-cyan hover:text-black"
                onClick={() => onOpenReview(item.id, item.name, orderId)}
                type="button"
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
        <div className="mt-2 border border-orange-500/20 bg-[#0c0c0c] p-3">
          {/* Show PROVISIONING only if payment is confirmed */}
          {item.orderRawStatus && item.orderRawStatus !== "pending" ? (
            <>
              <div className="mb-1 flex justify-between font-mono text-[10px] text-orange-400">
                <span className="flex items-center gap-1">
                  <Activity size={10} /> {t("orders.itemStatus.provisioning")}...
                </span>
                <span>
                  {t("orders.itemStatus.estimatedTime")}: {item.estimatedDelivery}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="relative mt-2 mb-2 h-1 w-full overflow-hidden bg-gray-800">
                <div
                  className="absolute top-0 left-0 h-full bg-orange-500 shadow-[0_0_10px_orange]"
                  style={{ width: `${item.progress || 0}%` }}
                />
                <div className="absolute top-0 left-0 h-full w-full animate-pulse bg-gradient-to-r from-transparent via-white/30 to-transparent" />
              </div>

              {/* Deadline with Countdown */}
              <div className="mt-2 flex items-center justify-between border-white/5 border-t pt-2">
                <p className="font-mono text-[10px] text-gray-500">
                  &gt; {t("orders.item.deadline")}: {item.deadline}
                </p>
                {item.deadlineRaw && !countdown.isExpired && (
                  <div className="flex items-center gap-1.5 rounded bg-orange-500/10 px-2 py-0.5 font-mono text-[10px] text-orange-400">
                    <Timer className="animate-pulse" size={10} />
                    <span>{countdown.formatted}</span>
                  </div>
                )}
                {countdown.isExpired && item.deadlineRaw && (
                  <div className="flex items-center gap-1 font-mono text-[10px] text-red-400">
                    <AlertTriangle size={10} />
                    <span>{t("orders.itemStatus.deadlineExpired")}</span>
                  </div>
                )}
              </div>
            </>
          ) : (
            /* For unpaid orders, show payment deadline only */
            item.deadline && (
              <p className="font-mono text-[10px] text-gray-500">
                &gt; {t("orders.item.deadline")}: {item.deadline}
              </p>
            )
          )}
        </div>
      )}

      {/* === REFUNDED === */}
      {item.status === "cancelled" && (
        <div className="mt-2 border border-red-500/20 bg-red-900/5 p-2 font-mono text-[10px] text-red-400">
          &gt; {item.reason}
        </div>
      )}
    </div>
  );
};

export default memo(OrderItem);
