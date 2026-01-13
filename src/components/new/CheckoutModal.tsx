/**
 * CheckoutModal
 *
 * UNIFIED CURRENCY ARCHITECTURE:
 * - Uses USD values (totalUsd, userBalanceUsd) for balance comparisons
 * - Uses display values (total, userBalance) for UI rendering
 * - Never mixes currencies in calculations
 */

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, Server } from "lucide-react";
import { formatPrice } from "../../utils/currency";
import { useLocale } from "../../hooks/useLocale";
import CartSummary from "./CartSummary";
import PaymentMethodSelector from "./PaymentMethodSelector";
import PaymentProcessing from "./PaymentProcessing";
import type { CartItem } from "../../types/component";
import type { APICreateOrderResponse } from "../../types/api";

export type PaymentMethod = "crystalpay" | "internal";

interface CheckoutModalProps {
  cart: CartItem[];
  // USD values (for calculations) - CRITICAL: use these for balance checks
  userBalanceUsd?: number;
  totalUsd?: number;
  // Display values (for UI)
  userBalance?: number;
  total?: number;
  originalTotal?: number;
  // Currency info
  currency?: string;
  exchangeRate?: number;
  // Promo
  promoCode?: string | null;
  promoDiscountPercent?: number | null;
  // Handlers
  onClose: () => void;
  onRemoveItem: (id: string | number) => void;
  onUpdateQuantity?: (id: string | number, quantity: number) => void;
  onPay?: (method: PaymentMethod) => Promise<APICreateOrderResponse | null>;
  onSuccess: () => void;
  onApplyPromo?: (code: string) => Promise<{ success: boolean; message?: string }>;
  onRemovePromo?: () => void;
  loading?: boolean;
  error?: string | null;
}

const CheckoutModal: React.FC<CheckoutModalProps> = ({
  cart,
  userBalanceUsd = 0,
  totalUsd: propsTotalUsd,
  userBalance = 0,
  total: propsTotal,
  currency = "USD",
  originalTotal,
  promoCode,
  promoDiscountPercent,
  onClose,
  onRemoveItem,
  onUpdateQuantity,
  onPay,
  onSuccess,
  onApplyPromo,
  onRemovePromo,
}) => {
  const { t } = useLocale();
  const [step, setStep] = useState<"cart" | "payment" | "processing" | "success">("cart");
  const [selectedPayment, setSelectedPayment] = useState<PaymentMethod>("crystalpay");
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(() => Math.random().toString(36).substring(2, 8).toUpperCase());

  // Calculate totals from cart items if not provided
  const { total, totalUsd } = useMemo(() => {
    // Use props if provided
    if (propsTotal !== undefined && propsTotalUsd !== undefined) {
      return { total: propsTotal, totalUsd: propsTotalUsd };
    }

    // Calculate from cart items
    let displayTotal = 0;
    let usdTotal = 0;

    if (cart && Array.isArray(cart)) {
      cart.forEach((item) => {
        const price = item?.price || 0;
        const priceUsd = item?.priceUsd || price;
        const quantity = item?.quantity || 1;
        displayTotal += price * quantity;
        usdTotal += priceUsd * quantity;
      });
    }

    return {
      total: propsTotal ?? displayTotal,
      totalUsd: propsTotalUsd ?? usdTotal,
    };
  }, [cart, propsTotal, propsTotalUsd]);

  // Helper: Schedule a single log append with delay
  const scheduleLogAppend = (log: string, delayMs: number) => {
    setTimeout(() => {
      setLogs((prev) => [...prev.slice(-4), log]);
    }, delayMs);
  };

  // Simulation logs for hacking aesthetic
  const simulateLogs = (method: PaymentMethod) => {
    const commonLogs = ["> INITIALIZING_SECURE_CHANNEL", "> HANDSHAKE_PROTOCOL_V4"];

    const crystalLogs = [
      "> RESOLVING_CRYSTAL_NODE...",
      "> GENERATING_INVOICE_ID",
      "> ESTABLISHING_BRIDGE_CONNECTION",
      "> WAITING_FOR_EXTERNAL_SIGNAL...",
      "> PAYMENT_GATEWAY: READY",
    ];

    const internalLogs = [
      "> CHECKING_LOCAL_WALLET_INTEGRITY...",
      "> BALANCE_CHECK: OK",
      "> FREEZING_ASSETS...",
      "> INTERNAL_TRANSFER_EXECUTED",
      "> LEDGER_UPDATED_SUCCESSFULLY",
    ];

    const targetLogs = method === "internal" ? internalLogs : crystalLogs;

    setLogs([...commonLogs]);

    targetLogs.forEach((log, index) => {
      scheduleLogAppend(log, 500 + index * 600);
    });
  };

  const handlePay = async () => {
    // CRITICAL: Compare in USD to avoid currency mismatch
    if (selectedPayment === "internal" && totalUsd > userBalanceUsd) {
      // Format error message in display currency for user
      const availableStr = formatPrice(userBalance, currency);
      const requiredStr = formatPrice(total, currency);
      setError(
        `Недостаточно средств на балансе. Доступно: ${availableStr}, требуется: ${requiredStr}`
      );
      return;
    }

    setError(null);
    setStep("processing");
    simulateLogs(selectedPayment);

    if (onPay) {
      try {
        const result = await onPay(selectedPayment);
        if (result && selectedPayment === "internal") {
          setTimeout(() => setStep("success"), 2000);
        }
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "PAYMENT_FAILED";
        setError(errorMessage);
        setStep("payment");
      }
    } else {
      // Demo mode
      setTimeout(() => setStep("success"), 4500);
    }
  };

  const closeSuccess = () => {
    onSuccess();
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
      />

      {/* Modal Window */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-2xl bg-[#080808] border border-white/20 shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-[#0a0a0a] relative z-20">
          <h2 className="text-xl font-display font-bold text-white flex items-center gap-2">
            <span className="w-1.5 h-6 bg-pandora-cyan block" />
            {t("checkout.title")}
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 relative z-10">
          <AnimatePresence mode="wait">
            {/* === STEP 1: CART REVIEW === */}
            {step === "cart" && (
              <CartSummary
                cart={cart}
                total={total}
                originalTotal={originalTotal}
                currency={currency}
                promoCode={promoCode}
                promoDiscountPercent={promoDiscountPercent}
                onRemoveItem={onRemoveItem}
                onUpdateQuantity={onUpdateQuantity}
                onProceed={() => setStep("payment")}
                onApplyPromo={onApplyPromo}
                onRemovePromo={onRemovePromo}
              />
            )}

            {/* === STEP 2: PAYMENT METHOD SELECTION === */}
            {step === "payment" && (
              <PaymentMethodSelector
                selectedPayment={selectedPayment}
                total={total}
                userBalance={userBalance}
                currency={currency}
                error={error}
                onSelectPayment={setSelectedPayment}
                onPay={handlePay}
              />
            )}

            {/* === STEP 3: PAYMENT PROCESSING === */}
            {step === "processing" && (
              <PaymentProcessing logs={logs} selectedPayment={selectedPayment} />
            )}

            {/* === STEP 4: SUCCESS === */}
            {step === "success" && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="py-12 sm:py-16 flex flex-col items-center justify-center text-center min-h-[400px]"
              >
                {/* Icon Container with proper spacing */}
                <div className="relative mb-8 pb-4">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
                    className="w-20 h-20 rounded-full bg-green-500/10 border-2 border-green-500 flex items-center justify-center mx-auto"
                  >
                    <CheckCircle size={48} className="text-green-500" />
                  </motion.div>
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                    className="absolute -bottom-1 left-1/2 -translate-x-1/2 text-[10px] font-mono text-green-500 bg-green-900/30 px-2 py-0.5 rounded whitespace-nowrap"
                  >
                    {t("checkout.success.status")}
                  </motion.div>
                </div>

                {/* Title with proper spacing */}
                <h3 className="text-xl sm:text-2xl font-display font-bold text-white mb-3 px-4">
                  {t("checkout.success.title")}
                </h3>

                {/* Description with proper spacing */}
                <p className="text-xs sm:text-sm font-mono text-gray-400 max-w-xs mb-8 px-4 leading-relaxed">
                  {t("checkout.success.description1")}
                  <br className="hidden sm:block" />
                  <span className="sm:hidden"> </span>
                  {t("checkout.success.description2")}
                </p>

                {/* Button with proper spacing */}
                <button
                  onClick={closeSuccess}
                  className="bg-white text-black font-bold py-3 px-8 hover:bg-gray-200 transition-colors text-sm sm:text-base"
                >
                  {t("checkout.success.button")}
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="p-4 bg-[#0a0a0a] border-t border-white/10 flex justify-between items-center text-[10px] font-mono text-gray-600 relative z-20">
          <div className="flex items-center gap-2">
            <Server size={10} />
            <span>{t("checkout.footer.secureChannel")}</span>
          </div>
          <div className="flex items-center gap-4">
            <span>
              {t("checkout.footer.session")}: {sessionId}
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default CheckoutModal;
