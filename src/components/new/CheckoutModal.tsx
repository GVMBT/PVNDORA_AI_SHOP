/**
 * CheckoutModal
 *
 * UNIFIED CURRENCY ARCHITECTURE:
 * - Uses USD values (totalUsd, userBalanceUsd) for balance comparisons
 * - Uses display values (total, userBalance) for UI rendering
 * - Never mixes currencies in calculations
 */

import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle, Server, X } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { useLocale } from "../../hooks/useLocale";
import type { APICreateOrderResponse } from "../../types/api";
import type { CartItem } from "../../types/component";
import { formatPrice } from "../../utils/currency";
import CartSummary from "./CartSummary";
import PaymentMethodSelector from "./PaymentMethodSelector";
import PaymentProcessing from "./PaymentProcessing";

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
  const [sessionId] = useState(() => {
    // Use crypto for session ID generation (security-sensitive)
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
      return crypto.randomUUID().slice(0, 8).toUpperCase().replaceAll("-", "");
    }
    // Fallback: timestamp-based ID (less secure but better than Math.random)
    return `S${Date.now().toString(36).slice(-7).toUpperCase()}`;
  });

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
      for (const item of cart) {
        const price = item?.price || 0;
        const priceUsd = item?.priceUsd || price;
        const quantity = item?.quantity || 1;
        displayTotal += price * quantity;
        usdTotal += priceUsd * quantity;
      }
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
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        exit={{ opacity: 0 }}
        initial={{ opacity: 0 }}
        onClick={onClose}
      />

      {/* Modal Window */}
      <motion.div
        animate={{ scale: 1, opacity: 1, y: 0 }}
        className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden border border-white/20 bg-[#080808] shadow-[0_0_50px_rgba(0,0,0,0.8)]"
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative z-20 flex items-center justify-between border-white/10 border-b bg-[#0a0a0a] p-6">
          <h2 className="flex items-center gap-2 font-bold font-display text-white text-xl">
            <span className="block h-6 w-1.5 bg-pandora-cyan" />
            {t("checkout.title")}
          </h2>
          <button
            className="text-gray-500 transition-colors hover:text-white"
            onClick={onClose}
            type="button"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content Body */}
        <div className="relative z-10 flex-1 overflow-y-auto p-6">
          <AnimatePresence mode="wait">
            {/* === STEP 1: CART REVIEW === */}
            {step === "cart" && (
              <CartSummary
                cart={cart}
                currency={currency}
                onApplyPromo={onApplyPromo}
                onProceed={() => setStep("payment")}
                onRemoveItem={onRemoveItem}
                onRemovePromo={onRemovePromo}
                onUpdateQuantity={onUpdateQuantity}
                originalTotal={originalTotal}
                promoCode={promoCode}
                promoDiscountPercent={promoDiscountPercent}
                total={total}
              />
            )}

            {/* === STEP 2: PAYMENT METHOD SELECTION === */}
            {step === "payment" && (
              <PaymentMethodSelector
                currency={currency}
                error={error}
                onPay={handlePay}
                onSelectPayment={setSelectedPayment}
                selectedPayment={selectedPayment}
                total={total}
                userBalance={userBalance}
              />
            )}

            {/* === STEP 3: PAYMENT PROCESSING === */}
            {step === "processing" && (
              <PaymentProcessing logs={logs} selectedPayment={selectedPayment} />
            )}

            {/* === STEP 4: SUCCESS === */}
            {step === "success" && (
              <motion.div
                animate={{ opacity: 1, scale: 1 }}
                className="flex min-h-[450px] flex-col items-center justify-center py-12 text-center sm:py-20"
                exit={{ opacity: 0, scale: 0.9 }}
                initial={{ opacity: 0, scale: 0.9 }}
                key="success"
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              >
                {/* Icon Container with enhanced visual effects */}
                <div className="relative mb-10 pb-6">
                  {/* Glow effect behind icon */}
                  <motion.div
                    animate={{ opacity: 1, scale: 1 }}
                    className="absolute inset-0 -top-2 -right-2 -bottom-2 -left-2 rounded-full bg-green-500/20 blur-xl"
                    initial={{ opacity: 0, scale: 0.8 }}
                    transition={{ delay: 0.1, duration: 0.6 }}
                  />

                  {/* Pulsing ring effect */}
                  <motion.div
                    animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.6, 0.3] }}
                    className="absolute inset-0 rounded-full border-2 border-green-500/40"
                    initial={{ scale: 0.8, opacity: 0 }}
                    transition={{
                      delay: 0.3,
                      duration: 2,
                      repeat: Number.POSITIVE_INFINITY,
                      ease: "easeInOut",
                    }}
                  />

                  {/* Main icon container */}
                  <motion.div
                    animate={{ scale: 1, rotate: 0 }}
                    className="relative mx-auto flex h-24 w-24 items-center justify-center rounded-full border-2 border-green-500 bg-green-500/10 shadow-[0_0_30px_rgba(34,197,94,0.3)] sm:h-28 sm:w-28"
                    initial={{ scale: 0, rotate: -180 }}
                    transition={{
                      delay: 0.2,
                      type: "spring",
                      stiffness: 200,
                      damping: 15,
                    }}
                  >
                    <motion.div
                      animate={{ scale: 1 }}
                      initial={{ scale: 0 }}
                      transition={{ delay: 0.4, type: "spring", stiffness: 300 }}
                    >
                      <CheckCircle
                        className="text-green-500 sm:h-14 sm:w-14"
                        size={56}
                        strokeWidth={2.5}
                      />
                    </motion.div>
                  </motion.div>

                  {/* Status badge with improved styling */}
                  <motion.div
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute -bottom-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-green-500/30 bg-green-950/60 px-3 py-1 font-bold font-mono text-[10px] text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.2)] backdrop-blur-sm"
                    initial={{ opacity: 0, y: 10 }}
                    transition={{ delay: 0.6, duration: 0.4 }}
                  >
                    {t("checkout.success.status")}
                  </motion.div>
                </div>

                {/* Title with improved typography and spacing */}
                <motion.h3
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-4 px-4 font-bold font-display text-2xl text-white tracking-tight sm:text-3xl"
                  initial={{ opacity: 0, y: 20 }}
                  transition={{ delay: 0.5, duration: 0.5 }}
                >
                  {t("checkout.success.title")}
                </motion.h3>

                {/* Description with better readability */}
                <motion.div
                  animate={{ opacity: 1, y: 0 }}
                  className="mb-10 max-w-sm space-y-2 px-4 font-mono text-gray-300 text-sm leading-relaxed sm:text-base"
                  initial={{ opacity: 0, y: 15 }}
                  transition={{ delay: 0.7, duration: 0.5 }}
                >
                  <p>{t("checkout.success.description1")}</p>
                  <p className="text-gray-400">{t("checkout.success.description2")}</p>
                </motion.div>

                {/* Enhanced button with better visual feedback */}
                <motion.button
                  animate={{ opacity: 1, y: 0 }}
                  className="group relative overflow-hidden bg-white px-10 py-4 font-bold font-display text-black text-sm uppercase tracking-wider shadow-[0_4px_20px_rgba(255,255,255,0.2)] transition-all duration-200 hover:bg-gray-100 hover:shadow-[0_6px_30px_rgba(255,255,255,0.3)] sm:px-12 sm:text-base"
                  initial={{ opacity: 0, y: 20 }}
                  onClick={closeSuccess}
                  transition={{ delay: 0.9, duration: 0.4 }}
                  type="button"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {/* Subtle shine effect on hover */}
                  <motion.div
                    className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/20 to-transparent transition-transform duration-700 group-hover:translate-x-full"
                    initial={false}
                  />
                  <span className="relative z-10">{t("checkout.success.button")}</span>
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="relative z-20 flex items-center justify-between border-white/10 border-t bg-[#0a0a0a] p-4 font-mono text-[10px] text-gray-600">
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
