/**
 * PaymentMethodSelector Component
 *
 * Displays payment method selection options.
 */

import { motion } from "framer-motion";
import { Bitcoin, Globe, Server, ShieldCheck, Wallet, Zap } from "lucide-react";
import type React from "react";
import { memo } from "react";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";
import type { PaymentMethod } from "./CheckoutModal";

interface PaymentMethodSelectorProps {
  selectedPayment: PaymentMethod;
  total: number;
  userBalance: number;
  currency: string;
  error?: string | null;
  onSelectPayment: (method: PaymentMethod) => void;
  onPay: () => void;
}

const PaymentMethodSelector: React.FC<PaymentMethodSelectorProps> = ({
  selectedPayment,
  total,
  userBalance,
  currency,
  error,
  onSelectPayment,
  onPay,
}) => {
  const { t } = useLocale();
  const canUseInternal = userBalance >= total;

  return (
    <motion.div
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      initial={{ opacity: 0, x: 20 }}
      key="payment"
    >
      <div className="mb-8">
        <h3 className="mb-4 flex items-center gap-2 font-mono text-pandora-cyan text-xs uppercase">
          <Server size={12} />
          {t("checkout.payment.selectNode")}
        </h3>

        {error && (
          <div className="mb-4 flex items-center gap-2 border border-red-500/30 bg-red-500/10 p-3 font-mono text-red-400 text-xs">
            <ShieldCheck size={14} /> {error}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {/* Option 1: Internal Balance */}
          <button
            className={`group relative flex flex-col items-center gap-3 overflow-hidden border p-4 text-center transition-all ${
              selectedPayment === "internal"
                ? "border-green-500 bg-green-500/5"
                : "border-white/10 bg-white/5 hover:bg-white/10"
            }`}
            onClick={() => onSelectPayment("internal")}
            type="button"
          >
            <div
              className={`rounded-full p-2 ${
                selectedPayment === "internal"
                  ? "bg-green-500 text-black"
                  : "bg-black text-gray-400"
              }`}
            >
              <Wallet size={20} />
            </div>
            <div>
              <div className="mb-1 font-bold text-white text-xs uppercase">
                {t("checkout.payment.internal")}
              </div>
              <div className="font-mono text-[10px] text-gray-500">
                {t("checkout.payment.balance", { amount: formatPrice(userBalance, currency) })}
              </div>
            </div>
            {selectedPayment === "internal" && (
              <div className="absolute top-1 right-1">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
              </div>
            )}
          </button>

          {/* Option 2: CrystalPay (Redirect) */}
          <button
            className={`group relative flex flex-col items-center gap-3 overflow-hidden border p-4 text-center transition-all ${
              selectedPayment === "crystalpay"
                ? "border-purple-500 bg-purple-500/5"
                : "border-white/10 bg-white/5 hover:bg-white/10"
            }`}
            onClick={() => onSelectPayment("crystalpay")}
            type="button"
          >
            <div
              className={`rounded-full p-2 ${
                selectedPayment === "crystalpay"
                  ? "bg-purple-500 text-white"
                  : "bg-black text-gray-400"
              }`}
            >
              <Globe size={20} />
            </div>
            <div>
              <div className="mb-1 font-bold text-white text-xs uppercase">
                {t("checkout.payment.crypto")}
              </div>
              <div className="font-mono text-[10px] text-gray-500">
                {t("checkout.payment.gateway")}
              </div>
            </div>
            {selectedPayment === "crystalpay" && (
              <div className="absolute top-1 right-1">
                <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-purple-500" />
              </div>
            )}
          </button>
        </div>

        {/* Dynamic Payment Interface */}
        <div className="relative mt-6 mb-8 rounded-sm border border-white/10 bg-[#0e0e0e] p-6">
          <div className="absolute top-0 left-0 h-2 w-2 border-white/20 border-t border-l" />
          <div className="absolute right-0 bottom-0 h-2 w-2 border-white/20 border-r border-b" />

          {selectedPayment === "internal" && (
            <div className="flex flex-col items-center justify-center py-2">
              <div className="mb-4 text-center">
                <div className="mb-1 font-bold font-display text-3xl text-white">
                  {formatPrice(total, currency)}
                </div>
                <div className="font-mono text-gray-500 text-xs">
                  {t("checkout.payment.debited")}
                </div>
              </div>
              <div className="flex items-center gap-2 border border-green-500/30 bg-green-900/10 px-3 py-1 font-mono text-green-500 text-xs">
                <Zap size={12} /> {t("checkout.payment.instant")}
              </div>
            </div>
          )}

          {selectedPayment === "crystalpay" && (
            <div className="py-4 text-center">
              <div className="mx-auto mb-4 flex h-16 w-16 animate-pulse items-center justify-center rounded-full border border-purple-500/30 bg-purple-500/10">
                <Bitcoin className="text-purple-400" size={32} />
              </div>
              <h4 className="mb-2 font-bold text-white uppercase">
                {t("checkout.payment.externalTitle")}
              </h4>
              <p className="mx-auto max-w-xs font-mono text-gray-400 text-xs leading-relaxed">
                {t("checkout.payment.externalDesc")}
              </p>
            </div>
          )}
        </div>
      </div>

      <button
        className={`relative flex w-full items-center justify-center gap-3 overflow-hidden py-4 font-bold text-black uppercase tracking-widest transition-all hover:bg-white disabled:cursor-not-allowed disabled:opacity-50 ${selectedPayment === "internal" ? "bg-green-500" : "bg-purple-500 text-white hover:text-purple-500"}
        `}
        disabled={selectedPayment === "internal" && !canUseInternal}
        onClick={onPay}
        type="button"
      >
        <span className="relative z-10 flex items-center gap-2">
          <ShieldCheck size={18} />
          {selectedPayment === "internal"
            ? t("checkout.payment.confirmDebit", { amount: formatPrice(total, currency) })
            : t("checkout.payment.openGateway", { amount: formatPrice(total, currency) })}
        </span>
        <div className="absolute inset-0 bg-white opacity-0 mix-blend-overlay transition-opacity hover:opacity-20" />
      </button>
    </motion.div>
  );
};

export default memo(PaymentMethodSelector);
