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
      key="payment"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
    >
      <div className="mb-8">
        <h3 className="text-xs font-mono text-pandora-cyan mb-4 uppercase flex items-center gap-2">
          <Server size={12} />
          {t("checkout.payment.selectNode")}
        </h3>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono flex items-center gap-2">
            <ShieldCheck size={14} /> {error}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Option 1: Internal Balance */}
          <button
            type="button"
            onClick={() => onSelectPayment("internal")}
            className={`relative p-4 border flex flex-col items-center text-center gap-3 transition-all overflow-hidden group ${
              selectedPayment === "internal"
                ? "border-green-500 bg-green-500/5"
                : "border-white/10 bg-white/5 hover:bg-white/10"
            }`}
          >
            <div
              className={`p-2 rounded-full ${
                selectedPayment === "internal"
                  ? "bg-green-500 text-black"
                  : "bg-black text-gray-400"
              }`}
            >
              <Wallet size={20} />
            </div>
            <div>
              <div className="text-xs font-bold text-white uppercase mb-1">
                {t("checkout.payment.internal")}
              </div>
              <div className="text-[10px] text-gray-500 font-mono">
                {t("checkout.payment.balance", { amount: formatPrice(userBalance, currency) })}
              </div>
            </div>
            {selectedPayment === "internal" && (
              <div className="absolute top-1 right-1">
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
              </div>
            )}
          </button>

          {/* Option 2: CrystalPay (Redirect) */}
          <button
            type="button"
            onClick={() => onSelectPayment("crystalpay")}
            className={`relative p-4 border flex flex-col items-center text-center gap-3 transition-all overflow-hidden group ${
              selectedPayment === "crystalpay"
                ? "border-purple-500 bg-purple-500/5"
                : "border-white/10 bg-white/5 hover:bg-white/10"
            }`}
          >
            <div
              className={`p-2 rounded-full ${
                selectedPayment === "crystalpay"
                  ? "bg-purple-500 text-white"
                  : "bg-black text-gray-400"
              }`}
            >
              <Globe size={20} />
            </div>
            <div>
              <div className="text-xs font-bold text-white uppercase mb-1">
                {t("checkout.payment.crypto")}
              </div>
              <div className="text-[10px] text-gray-500 font-mono">
                {t("checkout.payment.gateway")}
              </div>
            </div>
            {selectedPayment === "crystalpay" && (
              <div className="absolute top-1 right-1">
                <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
              </div>
            )}
          </button>
        </div>

        {/* Dynamic Payment Interface */}
        <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm mb-8 relative mt-6">
          <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/20" />
          <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/20" />

          {selectedPayment === "internal" && (
            <div className="flex flex-col items-center justify-center py-2">
              <div className="text-center mb-4">
                <div className="text-3xl font-display font-bold text-white mb-1">
                  {formatPrice(total, currency)}
                </div>
                <div className="text-xs font-mono text-gray-500">
                  {t("checkout.payment.debited")}
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono text-green-500 bg-green-900/10 px-3 py-1 border border-green-500/30">
                <Zap size={12} /> {t("checkout.payment.instant")}
              </div>
            </div>
          )}

          {selectedPayment === "crystalpay" && (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-purple-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-purple-500/30 animate-pulse">
                <Bitcoin size={32} className="text-purple-400" />
              </div>
              <h4 className="text-white font-bold uppercase mb-2">
                {t("checkout.payment.externalTitle")}
              </h4>
              <p className="text-xs font-mono text-gray-400 leading-relaxed max-w-xs mx-auto">
                {t("checkout.payment.externalDesc")}
              </p>
            </div>
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onPay}
        disabled={selectedPayment === "internal" && !canUseInternal}
        className={`
          w-full text-black font-bold py-4 hover:bg-white transition-all uppercase tracking-widest flex items-center justify-center gap-3 relative overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed
          ${selectedPayment === "internal" ? "bg-green-500" : "bg-purple-500 text-white hover:text-purple-500"}
        `}
      >
        <span className="relative z-10 flex items-center gap-2">
          <ShieldCheck size={18} />
          {selectedPayment === "internal"
            ? t("checkout.payment.confirmDebit", { amount: formatPrice(total, currency) })
            : t("checkout.payment.openGateway", { amount: formatPrice(total, currency) })}
        </span>
        <div className="absolute inset-0 bg-white mix-blend-overlay opacity-0 hover:opacity-20 transition-opacity" />
      </button>
    </motion.div>
  );
};

export default memo(PaymentMethodSelector);
