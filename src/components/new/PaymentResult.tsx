/**
 * PaymentResult Component
 *
 * Terminal-style UI shown after payment redirect.
 * Polls order status and displays progress logs.
 * Works for both Mini App (startapp) and Browser (/payment/result) flows.
 */

import React, { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cpu,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { API } from "../../config";
import { localStorage } from "../../utils/storage";
import { getApiHeaders } from "../../utils/apiHeaders";
import { logger } from "../../utils/logger";
import { apiRequest } from "../../utils/apiClient";
import { randomFloat } from "../../utils/random";
import { PAYMENT_STATUS_MESSAGES, type PaymentStatus } from "../../constants";
import { useLocale } from "../../hooks/useLocale";

interface PaymentResultProps {
  orderId: string;
  isTopUp?: boolean; // True if this is a balance top-up, not an order
  onComplete: () => void;
  onViewOrders: () => void; // For topup, this navigates to profile
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
  const isTelegramMiniApp = typeof window !== "undefined" && !!(window as any).Telegram?.WebApp;

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

  // Check order/topup status
  const checkStatus = useCallback(async () => {
    try {
      // Use different endpoint for topup vs order
      const endpoint = isTopUp ? `/profile/topup/${orderId}/status` : `/orders/${orderId}/status`;

      // Use apiClient for consistent error handling
      // Note: We need to handle 404 specially, so we'll catch and check
      try {
        const data = await apiRequest<OrderStatusResponse>(endpoint);

        // Map backend status to our status type
        const backendStatus = data.status?.toLowerCase() || "unknown";
        let newStatus: PaymentStatus = "unknown";

        if (["delivered", "completed", "ready"].includes(backendStatus)) {
          newStatus = "delivered";
        } else if (["paid", "processing"].includes(backendStatus)) {
          newStatus = "paid";
        } else if (backendStatus === "partial") {
          newStatus = "partial";
        } else if (["pending", "awaiting_payment"].includes(backendStatus)) {
          newStatus = "pending";
        } else if (["expired", "cancelled"].includes(backendStatus)) {
          newStatus = "expired";
        } else if (["failed", "refunded"].includes(backendStatus)) {
          newStatus = "failed";
        } else if (backendStatus === "prepaid") {
          newStatus = "paid"; // Prepaid means payment confirmed, waiting for stock
        }

        return { status: newStatus, data };
      } catch (error: unknown) {
        // Handle 404 specifically - order might not exist yet or invalid ID
        const errorMessage = error instanceof Error ? error.message : String(error);
        if (errorMessage.includes("404") || errorMessage.includes("ORDER_NOT_FOUND")) {
          return {
            status: "unknown" as PaymentStatus,
            error: new Error("ORDER_NOT_FOUND"),
            httpStatus: 404,
          };
        }
        throw error;
      }
    } catch (error: unknown) {
      const errorInstance = error instanceof Error ? error : new Error(String(error));
      logger.error("Status check failed", errorInstance);
      return {
        status: "unknown" as PaymentStatus,
        error: errorInstance,
      };
    }
  }, [orderId, isTopUp]);

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
      const delay = Math.min(
        INITIAL_POLL_DELAY * Math.pow(BACKOFF_MULTIPLIER, attempt),
        MAX_POLL_DELAY
      );
      return delay;
    };

    const poll = async () => {
      if (shouldStop || isComplete) return;

      currentAttempt++;
      setPollCount(currentAttempt);

      // Check if we've exceeded max attempts
      if (currentAttempt > MAX_POLL_ATTEMPTS) {
        addLog(t("paymentResult.logs.timeout", { max: String(MAX_POLL_ATTEMPTS) }), "warning");
        addLog(t("paymentResult.logs.infoProcessing"), "info");
        setIsComplete(true);
        shouldStop = true;
        return;
      }

      addLog(t("paymentResult.logs.scan"), "info");

      const result = await checkStatus();

      // Handle 404 specifically
      if (
        result.httpStatus === 404 ||
        (result.error && result.error.message === "ORDER_NOT_FOUND")
      ) {
        consecutive404sRef.current += 1;
        const new404Count = consecutive404sRef.current;

        // If we get multiple consecutive 404s, order likely doesn't exist
        if (new404Count >= 3) {
          addLog(t("paymentResult.logs.errorNotFound"), "error");
          addLog(t("paymentResult.logs.infoVerifyOrder"), "info");
          setStatus("failed");
          setIsComplete(true);
          shouldStop = true;
          return;
        }

        // First few 404s might be temporary (order not yet in DB after redirect)
        if (currentAttempt <= 3) {
          addLog(t("paymentResult.logs.waitOrder"), "warning");
        } else {
          addLog(t("paymentResult.logs.warnNotFound"), "warning");
        }
      } else {
        // Reset 404 counter on successful response
        if (consecutive404sRef.current > 0) {
          consecutive404sRef.current = 0;
        }

        // Handle successful response
        if (result.status !== "unknown" || !result.error) {
          setStatus(result.status);

          switch (result.status) {
            case "delivered":
              addLog(t("paymentResult.logs.recvConfirmedGateway"), "success");
              if (isTopUp) {
                addLog(t("paymentResult.logs.execBalance"), "success");
                addLog(t("paymentResult.logs.doneTopup"), "success");
              } else {
                addLog(t("paymentResult.logs.execDelivery"), "success");
                addLog(t("paymentResult.logs.doneAllTransferred"), "success");
              }
              setProgress(100);
              setIsComplete(true);
              shouldStop = true;
              break;
            case "paid":
              addLog(t("paymentResult.logs.recvConfirmed"), "success");
              if (isTopUp) {
                addLog(t("paymentResult.logs.execBalance"), "success");
                addLog(t("paymentResult.logs.doneTopup"), "success");
              } else {
                addLog(t("paymentResult.logs.execOrderConfirmed"), "success");
                addLog(t("paymentResult.logs.doneCheckOrders"), "success");
              }
              setProgress(100);
              setIsComplete(true);
              shouldStop = true;
              break;
            case "partial":
              addLog(t("paymentResult.logs.recvConfirmed"), "success");
              addLog(t("paymentResult.logs.execSomeDelivered"), "success");
              addLog(t("paymentResult.logs.infoPreorder"), "info");
              addLog(t("paymentResult.logs.doneFullStatus"), "success");
              setProgress(100);
              setIsComplete(true);
              shouldStop = true;
              break;
            case "prepaid":
              addLog(t("paymentResult.logs.recvConfirmed"), "success");
              addLog(t("paymentResult.logs.infoPreorderQueue"), "info");
              addLog(t("paymentResult.logs.doneCheckOrders"), "success");
              setProgress(100);
              setIsComplete(true);
              shouldStop = true;
              break;
            case "pending":
              addLog(t("paymentResult.logs.waitPayment"), "warning");
              break;
            case "expired":
            case "failed":
              addLog(t("paymentResult.logs.failPayment", { status: result.status }), "error");
              setIsComplete(true);
              shouldStop = true;
              break;
            default:
              if (result.error) {
                addLog(t("paymentResult.logs.warnDelayed"), "warning");
              }
          }
        } else if (result.error) {
          // Generic error handling
          addLog(t("paymentResult.logs.warnDelayed"), "warning");
        }
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
              const urlParams = new URLSearchParams(window.location.search);
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
                className={`h-full ${isSuccess ? "bg-green-500" : isFailed ? "bg-red-500" : "bg-purple-500"}`}
                style={{
                  boxShadow: `0 0 10px ${isSuccess ? "#22c55e" : isFailed ? "#ef4444" : "#a855f7"}`,
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
                  <span
                    className={
                      log.type === "success"
                        ? "text-green-500"
                        : log.type === "error"
                          ? "text-red-500"
                          : log.type === "warning"
                            ? "text-orange-500"
                            : "text-gray-400"
                    }
                  >
                    {log.message}
                  </span>
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
                    onClick={() => window.location.reload()}
                    className="w-full py-3 bg-white/10 text-white font-bold text-sm flex items-center justify-center gap-2 hover:bg-white/20 transition-colors"
                  >
                    <RefreshCw size={16} />
                    RETRY
                  </button>
                  <button
                    onClick={onViewOrders}
                    className="w-full py-2 bg-transparent border border-white/20 text-gray-400 text-xs font-mono hover:border-white/40 transition-colors"
                  >
                    CHECK_ORDERS_MANUALLY
                  </button>
                </>
              )}

              <button
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
