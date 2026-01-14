/**
 * PaymentResult Component
 *
 * Terminal-style UI shown after payment redirect.
 * Polls order status and displays progress logs.
 * Works for both Mini App (startapp) and Browser (/payment/result) flows.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Clock,
  Cpu,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { PAYMENT_STATUS_MESSAGES, type PaymentStatus } from "../../constants";
import { useLocale } from "../../hooks/useLocale";
import { apiRequest } from "../../utils/apiClient";
import { logger } from "../../utils/logger";
import { randomFloat } from "../../utils/random";

// Helper functions for status-based styling (avoid nested ternaries)
type StatusState = "success" | "failed" | "pending";

const getStatusState = (isSuccess: boolean, isFailed: boolean): StatusState => {
  if (isSuccess) return "success";
  if (isFailed) return "failed";
  return "pending";
};

const getProgressBarColor = (state: StatusState): string => {
  if (state === "success") return "bg-green-500";
  if (state === "failed") return "bg-red-500";
  return "bg-purple-500";
};

const getProgressGlowColor = (state: StatusState): string => {
  if (state === "success") return "#22c55e";
  if (state === "failed") return "#ef4444";
  return "#a855f7";
};

const getLogTypeColor = (type: string): string => {
  if (type === "success") return "text-green-500";
  if (type === "error") return "text-red-500";
  if (type === "warning") return "text-orange-500";
  return "text-gray-400";
};

interface PaymentResultProps {
  readonly orderId: string;
  readonly isTopUp?: boolean; // True if this is a balance top-up, not an order
  readonly onComplete: () => void;
  readonly onViewOrders: () => void; // For topup, this navigates to profile
}

interface OrderStatusResponse {
  status: string;
  payment_confirmed?: boolean;
  items_delivered?: number;
  items_total?: number;
}

// Terminal log entry
interface LogEntry {
  timestamp: string;
  message: string;
  type: "info" | "success" | "error" | "warning";
}

// Constants for polling strategy
const MAX_POLL_ATTEMPTS = 15; // Maximum number of polling attempts
const INITIAL_POLL_DELAY = 1000; // Start with 1 second delay
const MAX_POLL_DELAY = 16000; // Maximum delay of 16 seconds between polls
const BACKOFF_MULTIPLIER = 2; // Exponential backoff multiplier

export function PaymentResult({
  orderId,
  isTopUp = false,
  onComplete,
  onViewOrders,
}: PaymentResultProps) {
  const { t } = useLocale();
  const [status, setStatus] = useState<PaymentStatus>("checking");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [pollCount, setPollCount] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const consecutive404sRef = useRef(0); // Use ref to avoid triggering effect re-runs

  // Check if we're in Telegram Mini App or external browser
  const isTelegramMiniApp =
    globalThis.window !== undefined &&
    !!(globalThis.window as unknown as { Telegram?: { WebApp?: unknown } }).Telegram?.WebApp;

  // Add log entry
  const addLog = useCallback((message: string, type: LogEntry["type"] = "info") => {
    const timestamp = new Date().toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    setLogs((prev) => [...prev.slice(-9), { timestamp, message, type }]);
  }, []);

  // Helper to map backend status to PaymentStatus (reduces cognitive complexity)
  const mapBackendStatus = useCallback((backendStatus: string): PaymentStatus => {
    const status = backendStatus.toLowerCase();
    if (["delivered", "completed", "ready"].includes(status)) return "delivered";
    if (["paid", "processing"].includes(status)) return "paid";
    if (status === "prepaid") return "prepaid";
    if (status === "partial") return "partial";
    if (["pending", "awaiting_payment"].includes(status)) return "pending";
    if (["expired", "cancelled"].includes(status)) return "expired";
    if (["failed", "refunded"].includes(status)) return "failed";
    return "unknown";
  }, []);

  // Helper to handle 404 errors (reduces cognitive complexity)
  const handle404Error = useCallback(
    (error: unknown): { status: PaymentStatus; error: Error; httpStatus: number } | null => {
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes("404") || errorMessage.includes("ORDER_NOT_FOUND")) {
        return {
          status: "unknown" as PaymentStatus,
          error: new Error("ORDER_NOT_FOUND"),
          httpStatus: 404,
        };
      }
      return null;
    },
    []
  );

  // Check order/topup status
  const checkStatus = useCallback(async () => {
    try {
      const endpoint = isTopUp ? `/profile/topup/${orderId}/status` : `/orders/${orderId}/status`;

      try {
        const data = await apiRequest<OrderStatusResponse>(endpoint);
        const backendStatus = data.status?.toLowerCase() || "unknown";
        const newStatus = mapBackendStatus(backendStatus);
        return { status: newStatus, data };
      } catch (error: unknown) {
        const notFoundResult = handle404Error(error);
        if (notFoundResult) return notFoundResult;
        throw error;
      }
    } catch (error: unknown) {
      let errorMessage: string;
      let errorInstance: Error;
      
      if (error instanceof Error) {
        errorInstance = error;
        errorMessage = error.message;
      } else if (error) {
        errorMessage = String(error);
        errorInstance = new Error(errorMessage);
      } else {
        errorMessage = "Unknown error";
        errorInstance = new Error(errorMessage);
      }
      
      logger.error("Status check failed", errorInstance);
      return {
        status: "unknown" as PaymentStatus,
        error: errorInstance,
      };
    }
  }, [orderId, isTopUp, handle404Error, mapBackendStatus]);

  // Polling effect with exponential backoff
  // Only run polling in Telegram Mini App (browser shows simple static page)
  useEffect(() => {
    if (isComplete) return;
    if (!isTelegramMiniApp) return; // No polling in browser

    addLog(
      isTopUp ? t("paymentResult.logs.initTopup") : t("paymentResult.logs.initPayment"),
      "info"
    );
    addLog(
      t(isTopUp ? "paymentResult.logs.targetTopup" : "paymentResult.logs.targetOrder", {
        id: orderId.slice(0, 8).toUpperCase(),
      }),
      "info"
    );

    let pollTimeout: NodeJS.Timeout | null = null;
    let progressInterval: NodeJS.Timeout;
    let currentAttempt = 0;
    let shouldStop = false;

    const calculateDelay = (attempt: number): number => {
      // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max)
      const delay = Math.min(INITIAL_POLL_DELAY * BACKOFF_MULTIPLIER ** attempt, MAX_POLL_DELAY);
      return delay;
    };

    // Helper to handle 404 errors (reduces cognitive complexity)
    const handle404Response = (
      result: Awaited<ReturnType<typeof checkStatus>>,
      attempt: number
    ): boolean => {
      const is404 = result.httpStatus === 404 || result.error?.message === "ORDER_NOT_FOUND";
      if (!is404) return false;

      consecutive404sRef.current += 1;
      const new404Count = consecutive404sRef.current;

      if (new404Count >= 3) {
        addLog(t("paymentResult.logs.errorNotFound"), "error");
        addLog(t("paymentResult.logs.infoVerifyOrder"), "info");
        setStatus("failed");
        setIsComplete(true);
        return true; // shouldStop
      }

      if (attempt <= 3) {
        addLog(t("paymentResult.logs.waitOrder"), "warning");
      } else {
        addLog(t("paymentResult.logs.warnNotFound"), "warning");
      }
      return false;
    };

    // Helper to complete polling with success (reduces cognitive complexity)
    const completePolling = () => {
      setProgress(100);
      setIsComplete(true);
      return true; // shouldStop
    };

    // Helper to handle status updates (reduces cognitive complexity)
    const handleStatusUpdate = (status: PaymentStatus): boolean => {
      setStatus(status);

      if (status === "delivered") {
        addLog(t("paymentResult.logs.recvConfirmedGateway"), "success");
        if (isTopUp) {
          addLog(t("paymentResult.logs.execBalance"), "success");
          addLog(t("paymentResult.logs.doneTopup"), "success");
        } else {
          addLog(t("paymentResult.logs.execDelivery"), "success");
          addLog(t("paymentResult.logs.doneAllTransferred"), "success");
        }
        return completePolling();
      }

      if (status === "paid") {
        addLog(t("paymentResult.logs.recvConfirmed"), "success");
        if (isTopUp) {
          addLog(t("paymentResult.logs.execBalance"), "success");
          addLog(t("paymentResult.logs.doneTopup"), "success");
        } else {
          addLog(t("paymentResult.logs.execOrderConfirmed"), "success");
          addLog(t("paymentResult.logs.doneCheckOrders"), "success");
        }
        return completePolling();
      }

      if (status === "partial") {
        addLog(t("paymentResult.logs.recvConfirmed"), "success");
        addLog(t("paymentResult.logs.execSomeDelivered"), "success");
        addLog(t("paymentResult.logs.infoPreorder"), "info");
        addLog(t("paymentResult.logs.doneFullStatus"), "success");
        return completePolling();
      }

      if (status === "prepaid") {
        addLog(t("paymentResult.logs.recvConfirmed"), "success");
        addLog(t("paymentResult.logs.infoPreorderQueue"), "info");
        addLog(t("paymentResult.logs.doneCheckOrders"), "success");
        return completePolling();
      }

      if (status === "pending") {
        addLog(t("paymentResult.logs.waitPayment"), "warning");
        return false;
      }

      if (status === "expired" || status === "failed") {
        addLog(t("paymentResult.logs.failPayment", { status }), "error");
        setIsComplete(true);
        return true;
      }

      return false;
    };

    const poll = async () => {
      if (shouldStop || isComplete) return;

      currentAttempt++;
      setPollCount(currentAttempt);

      if (currentAttempt > MAX_POLL_ATTEMPTS) {
        addLog(t("paymentResult.logs.timeout", { max: String(MAX_POLL_ATTEMPTS) }), "warning");
        addLog(t("paymentResult.logs.infoProcessing"), "info");
        setIsComplete(true);
        shouldStop = true;
        return;
      }

      addLog(t("paymentResult.logs.scan"), "info");
      const result = await checkStatus();

      // Handle 404 errors
      if (handle404Response(result, currentAttempt)) {
        shouldStop = true;
        return;
      }

      // Reset 404 counter on successful response
      if (consecutive404sRef.current > 0) {
        consecutive404sRef.current = 0;
      }

      // Handle successful response
      if (result.status !== "unknown" || !result.error) {
        shouldStop = handleStatusUpdate(result.status);
      } else if (result.error) {
        addLog(t("paymentResult.logs.warnDelayed"), "warning");
      }

      // Schedule next poll if we should continue
      if (!shouldStop && !isComplete && currentAttempt < MAX_POLL_ATTEMPTS) {
        const delay = calculateDelay(currentAttempt - 1);
        const delaySeconds = (delay / 1000).toFixed(1);

        if (currentAttempt > 1) {
          addLog(
            t("paymentResult.logs.next", {
              delay: delaySeconds,
              current: String(currentAttempt),
              max: String(MAX_POLL_ATTEMPTS),
            }),
            "info"
          );
        }

        pollTimeout = setTimeout(() => {
          poll();
        }, delay);
      }
    };

    // Start first poll immediately
    poll();

    // Progress animation (cosmetic)
    progressInterval = setInterval(() => {
      if (!shouldStop && !isComplete) {
        setProgress((prev) => {
          if (prev >= 90) return prev; // Cap at 90% until complete
          return prev + randomFloat(0.5, 5);
        });
      }
    }, 500);

    // Cleanup
    return () => {
      shouldStop = true;
      if (pollTimeout) {
        clearTimeout(pollTimeout);
      }
      clearInterval(progressInterval);
    };
  }, [orderId, addLog, checkStatus, isComplete, isTelegramMiniApp, t, isTopUp]);

  const statusInfo = PAYMENT_STATUS_MESSAGES[status];
  const isSuccess =
    status === "delivered" || status === "paid" || status === "partial" || status === "prepaid";
  const isFailed =
    status === "expired" ||
    status === "failed" ||
    (status === "unknown" && isComplete && consecutive404sRef.current >= 3);

  // For external browser: show simple "Return to Telegram" message
  // Polling happens in Mini App, no need to duplicate here
  if (!isTelegramMiniApp) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-sm text-center"
        >
          {/* Success Icon */}
          <div className="mb-6">
            <div className="w-20 h-20 mx-auto bg-green-500/20 border border-green-500/50 rounded-full flex items-center justify-center">
              <CheckCircle size={40} className="text-green-500" />
            </div>
          </div>

          {/* Message */}
          <h1 className="text-2xl font-bold text-white mb-2">Payment Received!</h1>
          <p className="text-gray-400 mb-8">
            Your order is being processed.
            <br />
            Return to Telegram to check status.
          </p>

          {/* Order ID */}
          <div className="bg-white/5 border border-white/10 rounded-lg p-3 mb-6">
            <div className="text-xs text-gray-500 mb-1">Order ID</div>
            <div className="font-mono text-pandora-cyan">{orderId.slice(0, 8).toUpperCase()}</div>
          </div>

          {/* Return to Telegram Button */}
          {/* Check URL params to determine which bot to return to */}
          <a
            href={(() => {
              const urlParams = new URLSearchParams(globalThis.location.search);
              const source = urlParams.get("source");
              // If source=discount, return to discount bot, otherwise main bot
              const botUsername =
                source === "discount"
                  ? import.meta.env.VITE_DISCOUNT_BOT_USERNAME || "ai_discount_hub_bot"
                  : import.meta.env.VITE_BOT_USERNAME || "pvndora_ai_bot";
              return `https://t.me/${botUsername}`;
            })()}
            className="block w-full py-4 bg-[#2AABEE] hover:bg-[#229ED9] text-white font-bold rounded-xl transition-colors mb-4"
          >
            Open Telegram
          </a>

          <p className="text-xs text-gray-600">You can close this tab now</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="font-mono text-xs text-gray-500 mb-2">{t("paymentResult.subtitle")}</div>
          <div className="font-display text-2xl font-bold text-white tracking-wider">
            {t("paymentResult.title")}
          </div>
        </div>

        {/* Main Terminal Card */}
        <div className="bg-[#080808] border border-white/10 overflow-hidden">
          {/* Status Header */}
          <div className={`p-4 border-b border-white/10 bg-${statusInfo.color}-500/10`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {status === "checking" && (
                  <div className="relative">
                    <div className="w-10 h-10 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
                    <Cpu size={16} className="absolute inset-0 m-auto text-purple-500" />
                  </div>
                )}
                {isSuccess && <CheckCircle size={24} className="text-green-500" />}
                {isFailed && <XCircle size={24} className="text-red-500" />}
                {status === "pending" && (
                  <Clock size={24} className="text-orange-500 animate-pulse" />
                )}
                {status === "unknown" && <AlertTriangle size={24} className="text-gray-500" />}

                <div>
                  <div className={`font-mono text-sm font-bold text-${statusInfo.color}-500`}>
                    [ {statusInfo.label} ]
                  </div>
                  <div className="text-xs text-gray-400">{statusInfo.description}</div>
                </div>
              </div>

              <div className="font-mono text-xs text-gray-500">
                ID: {orderId.slice(0, 8).toUpperCase()}
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="px-4 py-3 border-b border-white/5">
            <div className="flex justify-between text-[10px] font-mono text-gray-500 mb-1">
              <span>{t("paymentResult.verificationProgress")}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                className={`h-full ${getProgressBarColor(getStatusState(isSuccess, isFailed))}`}
                style={{
                  boxShadow: `0 0 10px ${getProgressGlowColor(getStatusState(isSuccess, isFailed))}`,
                }}
              />
            </div>
          </div>

          {/* Terminal Logs */}
          <div className="p-4 bg-black/50 h-48 overflow-hidden font-mono text-[10px] flex flex-col justify-end">
            <AnimatePresence mode="popLayout">
              {logs.map((log, i) => (
                <motion.div
                  key={`${log.timestamp}-${i}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-1 flex gap-2"
                >
                  <span className="text-gray-600">{log.timestamp}</span>
                  <span className={getLogTypeColor(log.type)}>{log.message}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            <div className="w-2 h-4 bg-gray-600 animate-pulse mt-1" />
          </div>

          {/* Actions - Mini App only (browser has separate UI) */}
          {isComplete && (
            <div className="p-4 border-t border-white/10 space-y-3">
              {isSuccess && (
                <button
                  type="button"
                  onClick={onViewOrders}
                  className="w-full py-3 bg-pandora-cyan text-black font-bold text-sm flex items-center justify-center gap-2 hover:bg-pandora-cyan/90 transition-colors"
                >
                  {t("paymentResult.viewOrders")}
                  <ArrowRight size={16} />
                </button>
              )}

              {(isFailed ||
                (status === "unknown" && isComplete && consecutive404sRef.current >= 3)) && (
                <>
                  <button
                    type="button"
                    onClick={() => globalThis.location.reload()}
                    className="w-full py-3 bg-white/10 text-white font-bold text-sm flex items-center justify-center gap-2 hover:bg-white/20 transition-colors"
                  >
                    <RefreshCw size={16} />
                    RETRY
                  </button>
                  <button
                    type="button"
                    onClick={onViewOrders}
                    className="w-full py-2 bg-transparent border border-white/20 text-gray-400 text-xs font-mono hover:border-white/40 transition-colors"
                  >
                    CHECK_ORDERS_MANUALLY
                  </button>
                </>
              )}

              <button
                type="button"
                onClick={onComplete}
                className="w-full py-2 bg-transparent border border-white/20 text-gray-400 text-xs font-mono hover:border-white/40 transition-colors"
              >
                {t("paymentResult.returnToCatalog")}
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-4 font-mono text-[10px] text-gray-600">
          {!isComplete && (
            <span className="animate-pulse">LIVE CONNECTION • Poll #{pollCount}</span>
          )}
          {isComplete && <span>{t("paymentResult.connectionClosed")}</span>}
        </div>
      </motion.div>
    </div>
  );
}

export default PaymentResult;
