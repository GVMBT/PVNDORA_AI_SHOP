/**
 * CyberModal - Unified cyberpunk-style modal system
 *
 * Replaces native window.prompt, alert, and confirm dialogs
 * with styled modals matching PVNDORA aesthetic.
 */

import React, { useState, useEffect, useCallback, createContext, useContext, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  AlertTriangle,
  CheckCircle,
  Info,
  Wallet,
  ArrowUpRight,
  Plus,
  Loader2,
} from "lucide-react";
import { getCurrencySymbol } from "../../utils/currency";
import { useLocaleContext } from "../../contexts/LocaleContext";
import { useLocale } from "../../hooks/useLocale";

// Helper functions for button styling (avoid nested ternaries)
const getButtonClassName = (type: string, icon?: string): string => {
  if (type === "withdraw") return "bg-purple-500 hover:bg-purple-400 text-white";
  if (type === "alert" && icon === "warning") return "bg-orange-500 hover:bg-orange-400 text-white";
  return "bg-pandora-cyan hover:bg-white text-black";
};

const getButtonText = (
  type: string,
  t: (key: string) => string
): string => {
  if (type === "topup") return t("modal.topUp.button");
  if (type === "withdraw") return t("modal.withdraw.button");
  if (type === "alert") return t("modal.ok");
  return t("modal.confirm");
};

// ==================== TYPES ====================

type ModalType = "prompt" | "confirm" | "alert" | "topup" | "withdraw";

interface ModalButton {
  label: string;
  variant?: "primary" | "secondary" | "danger";
  value?: string | boolean;
}

interface ModalConfig {
  type: ModalType;
  title: string;
  message?: string;
  icon?: "warning" | "success" | "info" | "wallet" | "withdraw";

  // For prompt type
  placeholder?: string;
  defaultValue?: string;
  inputType?: "text" | "number";

  // For topup/withdraw
  currency?: string;
  balance?: number;
  minAmount?: number;
  maxAmount?: number;
  previewWithdrawal?: (amount: number) => Promise<{
    amount_requested: number;
    amount_usdt_gross: number;
    network_fee: number;
    amount_usdt_net: number;
    can_withdraw: boolean;
  }>;

  // Buttons
  buttons?: ModalButton[];

  // Callbacks - supports various callback signatures
  onConfirm?:
    | ((value?: string | number) => void | Promise<void>)
    | ((amount: number, method: string, details: string) => Promise<void>);
  onCancel?: () => void;
}

interface ModalState extends ModalConfig {
  isOpen: boolean;
  isLoading?: boolean;
}

// Types for modal submit values
type ModalSubmitValue =
  | string
  | number
  | { amount: number; method: string; details: string }
  | undefined;

interface CyberModalContextType {
  showModal: (config: ModalConfig) => void;
  hideModal: () => void;
  showTopUp: (config: {
    currency: string;
    balance: number;
    minAmount: number;
    onConfirm: (amount: number) => Promise<void>;
  }) => void;
  showWithdraw: (config: {
    currency: string;
    balance: number;
    minAmount: number;
    maxAmount?: number;
    previewWithdrawal?: (amount: number) => Promise<{
      amount_requested: number;
      amount_usdt_gross: number;
      network_fee: number;
      amount_usdt_net: number;
      can_withdraw: boolean;
    }>;
    onConfirm: (amount: number, method: string, details: string) => Promise<void>;
  }) => void;
  showConfirm: (title: string, message: string, onConfirm: () => void) => void;
  showAlert: (title: string, message: string, icon?: "warning" | "success" | "info") => void;
}

// ==================== CONTEXT ====================

const CyberModalContext = createContext<CyberModalContextType | null>(null);

export const useCyberModal = () => {
  const context = useContext(CyberModalContext);
  if (!context) {
    throw new Error("useCyberModal must be used within CyberModalProvider");
  }
  return context;
};

// ==================== MODAL COMPONENT ====================

const Modal: React.FC<{
  state: ModalState;
  onClose: () => void;
  onSubmit: (value?: ModalSubmitValue) => void;
}> = ({ state, onClose, onSubmit }) => {
  const [inputValue, setInputValue] = useState(state.defaultValue || "");
  const [withdrawMethod, setWithdrawMethod] = useState<"crypto">("crypto");
  const [withdrawDetails, setWithdrawDetails] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [withdrawPreview, setWithdrawPreview] = useState<{
    amount_usdt_gross: number;
    network_fee: number;
    amount_usdt_net: number;
    can_withdraw: boolean;
  } | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const { currency: contextCurrency } = useLocaleContext();
  const { t } = useLocale();

  // Convert preset amounts from USD to user currency
  // Base presets: 5, 10, 20, 50 USD (reasonable amounts for top-up)
  const getPresetAmounts = useMemo(() => {
    const usdPresets = [5, 10, 20, 50]; // Base presets in USD
    const targetCurrency = state.currency || contextCurrency || "USD";

    if (targetCurrency === "USD") {
      return usdPresets;
    }

    // Approximate exchange rates for UI display (backend will handle exact conversion)
    const rates: Record<string, number> = {
      RUB: 100, // 1 USD ≈ 100 RUB
      UAH: 40, // 1 USD ≈ 40 UAH
      EUR: 0.9, // 1 USD ≈ 0.9 EUR
      TRY: 30, // 1 USD ≈ 30 TRY
      INR: 80, // 1 USD ≈ 80 INR
      AED: 3.7, // 1 USD ≈ 3.7 AED
    };

    const rate = rates[targetCurrency] || 1;
    return usdPresets.map((amount) => Math.round(amount * rate));
  }, [state.currency, contextCurrency]);

  // Reset state when modal opens
  useEffect(() => {
    if (state.isOpen) {
      setInputValue(state.defaultValue || state.minAmount?.toString() || "");
      setWithdrawMethod("crypto");
      setWithdrawDetails("");
      setError(null);
      setWithdrawPreview(null);
    }
  }, [state.isOpen, state.defaultValue, state.minAmount]);

  // Fetch withdrawal preview when amount changes (for withdraw modal only)
  useEffect(() => {
    if (state.type === "withdraw" && state.isOpen && state.previewWithdrawal && inputValue) {
      const amount = Number.parseFloat(inputValue);
      if (!Number.isNaN(amount) && amount > 0 && amount <= (state.balance || 0)) {
        setLoadingPreview(true);
        state
          .previewWithdrawal(amount)
          .then((preview) => {
            setWithdrawPreview(preview);
            setLoadingPreview(false);
          })
          .catch((err) => {
            console.error("Failed to preview withdrawal:", err);
            setLoadingPreview(false);
          });
      } else {
        setWithdrawPreview(null);
      }
    }
  }, [state.type, state.isOpen, state.previewWithdrawal, state.balance, inputValue]);

  const handleSubmit = async () => {
    // Validate for topup/withdraw
    if (state.type === "topup" || state.type === "withdraw") {
      const amount = Number.parseFloat(inputValue);
      if (Number.isNaN(amount) || amount <= 0) {
        setError(t("modal.errors.enterAmount"));
        return;
      }
      if (state.minAmount && amount < state.minAmount) {
        setError(`${t("modal.errors.minAmount")}: ${state.minAmount} ${state.currency}`);
        return;
      }
      if (state.maxAmount && amount > state.maxAmount) {
        setError(`${t("modal.errors.maxAmount")}: ${state.maxAmount} ${state.currency}`);
        return;
      }
      if (state.type === "withdraw") {
        if (state.balance && amount > state.balance) {
          setError(t("modal.errors.insufficientFunds"));
          return;
        }
        if (withdrawPreview && !withdrawPreview.can_withdraw) {
          setError(
            "Сумма слишком мала. После комиссии вы получите менее 8.5 USDT (требование биржи: минимум 10 USD)."
          );
          return;
        }
        if (!withdrawDetails || !withdrawDetails.trim()) {
          setError("Укажите адрес кошелька");
          return;
        }
      }
      if (state.type === "withdraw" && !withdrawDetails.trim()) {
        setError(t("modal.errors.enterDetails"));
        return;
      }
    }

    setError(null);

    if (state.type === "withdraw") {
      onSubmit({
        amount: Number.parseFloat(inputValue),
        method: withdrawMethod,
        details: withdrawDetails,
      });
    } else if (state.type === "topup" || state.type === "prompt") {
      onSubmit(state.inputType === "number" ? Number.parseFloat(inputValue) : inputValue);
    } else {
      onSubmit(undefined);
    }
  };

  const getIcon = () => {
    const iconClass = "w-8 h-8";
    switch (state.icon) {
      case "warning":
        return <AlertTriangle className={`${iconClass} text-orange-500`} />;
      case "success":
        return <CheckCircle className={`${iconClass} text-green-500`} />;
      case "wallet":
        return <Wallet className={`${iconClass} text-pandora-cyan`} />;
      case "withdraw":
        return <ArrowUpRight className={`${iconClass} text-purple-500`} />;
      default:
        return <Info className={`${iconClass} text-pandora-cyan`} />;
    }
  };

  const currencySymbol = getCurrencySymbol(state.currency || "USD");

  return (
    <AnimatePresence>
      {state.isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          onClick={onClose}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            onClick={(e) => e.stopPropagation()}
            className="relative w-full max-w-md bg-[#0a0a0a] border border-white/10 shadow-2xl overflow-hidden"
          >
            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-pandora-cyan" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-pandora-cyan" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-pandora-cyan" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-pandora-cyan" />

            {/* Glow effect */}
            <div className="absolute -top-20 left-1/2 -translate-x-1/2 w-40 h-40 bg-pandora-cyan/10 blur-3xl pointer-events-none" />

            {/* Header */}
            <div className="relative px-6 pt-6 pb-4 border-b border-white/5">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                  {getIcon()}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-display font-bold text-white uppercase tracking-wider">
                    {state.title}
                  </h3>
                  {/* Show message in header only for non-alert/confirm types (like prompt) */}
                  {state.message && state.type !== "alert" && state.type !== "confirm" && (
                    <p className="text-xs text-gray-500 font-mono mt-1">{state.message}</p>
                  )}
                </div>
                <button
                  onClick={onClose}
                  className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-white hover:bg-white/10 transition-colors rounded"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="px-6 py-5">
              {/* TopUp Content */}
              {state.type === "topup" && (
                <div className="space-y-4">
                  {/* Balance Display */}
                  <div className="bg-white/5 border border-white/10 p-4 rounded">
                    <div className="text-[10px] text-gray-500 font-mono uppercase mb-1">
                      {t("modal.topUp.currentBalance")}
                    </div>
                    <div className="text-2xl font-display font-bold text-pandora-cyan">
                      {state.balance?.toLocaleString()} {currencySymbol}
                    </div>
                  </div>

                  {/* Amount Input */}
                  <div>
                    <label className="text-[10px] text-gray-500 font-mono uppercase mb-2 block">
                      {t("modal.topUp.amount")}
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={`Min: ${state.minAmount}`}
                        className="w-full bg-black border border-white/20 focus:border-pandora-cyan px-4 py-3 text-white font-mono text-lg outline-none transition-colors"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono">
                        {currencySymbol}
                      </span>
                    </div>
                  </div>

                  {/* Quick amounts */}
                  <div className="flex gap-2">
                    {getPresetAmounts.map((amount) => (
                      <button
                        key={amount}
                        onClick={() => setInputValue(String(amount))}
                        className={`flex-1 py-2 text-xs font-mono border transition-colors ${
                          inputValue === String(amount)
                            ? "bg-pandora-cyan/20 border-pandora-cyan text-pandora-cyan"
                            : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                        }`}
                      >
                        {amount.toLocaleString()}
                        {currencySymbol}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Withdraw Content */}
              {state.type === "withdraw" && (
                <div className="space-y-4">
                  {/* Balance Display */}
                  <div className="bg-white/5 border border-white/10 p-4 rounded">
                    <div className="text-[10px] text-gray-500 font-mono uppercase mb-1">
                      {t("modal.withdraw.availableBalance")}
                    </div>
                    <div className="text-2xl font-display font-bold text-green-500">
                      {state.balance?.toLocaleString()} {currencySymbol}
                    </div>
                  </div>

                  {/* Amount Input */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-[10px] text-gray-500 font-mono uppercase">
                        {t("modal.withdraw.amount")}
                      </label>
                      {state.maxAmount && state.maxAmount > 0 && (
                        <button
                          type="button"
                          onClick={() => {
                            setInputValue(state.maxAmount!.toString());
                          }}
                          className="text-[10px] text-purple-400 font-mono uppercase hover:text-purple-300 transition-colors"
                        >
                          {t("modal.withdraw.max") || "МАКС"}
                        </button>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        type="number"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={`Min: ${state.minAmount}`}
                        max={state.maxAmount || state.balance}
                        min={state.minAmount}
                        className="w-full bg-black border border-white/20 focus:border-purple-500 px-4 py-3 pr-16 text-white font-mono text-lg outline-none transition-colors"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono">
                        {currencySymbol}
                      </span>
                    </div>
                  </div>

                  {/* Withdrawal Preview (Fees and Final Amount) */}
                  {state.type === "withdraw" &&
                    withdrawPreview &&
                    !loadingPreview &&
                    Number.parseFloat(inputValue) > 0 && (
                      <div className="bg-white/5 border border-white/10 p-4 rounded space-y-2">
                        <div className="text-[10px] text-gray-500 font-mono uppercase mb-2">
                          {t("modal.withdraw.preview") || "РАСЧЁТ ВЫВОДА"}
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400 font-mono">Сумма (USDT):</span>
                          <span className="text-white font-mono font-bold">
                            {withdrawPreview.amount_usdt_gross.toFixed(2)} USDT
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400 font-mono">Комиссия сети:</span>
                          <span className="text-orange-400 font-mono">
                            -{withdrawPreview.network_fee.toFixed(2)} USDT
                          </span>
                        </div>
                        <div className="border-t border-white/10 pt-2 mt-2 flex justify-between">
                          <span className="text-gray-300 font-mono font-bold">К получению:</span>
                          <span className="text-green-400 font-mono font-bold text-lg">
                            {withdrawPreview.amount_usdt_net.toFixed(2)} USDT
                          </span>
                        </div>
                        {!withdrawPreview.can_withdraw && (
                          <div className="mt-2 px-2 py-1 bg-orange-500/10 border border-orange-500/30 text-orange-400 text-xs font-mono">
                            ⚠ После комиссии сумма слишком мала. Минимум: 8.5 USDT (требование
                            биржи: 10 USD)
                          </div>
                        )}
                      </div>
                    )}
                  {state.type === "withdraw" && loadingPreview && (
                    <div className="bg-white/5 border border-white/10 p-4 rounded text-center">
                      <Loader2 size={16} className="animate-spin mx-auto text-purple-400" />
                    </div>
                  )}

                  {/* Method Selection - Only Crypto (TRC20 USDT) */}
                  <div>
                    <label className="text-[10px] text-gray-500 font-mono uppercase mb-2 block">
                      {t("modal.withdraw.method")}
                    </label>
                    <div className="bg-purple-500/20 border border-purple-500 p-4 rounded">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">₿</span>
                        <div>
                          <div className="text-sm font-mono font-bold text-purple-400">
                            TRC20 USDT
                          </div>
                          <div className="text-[10px] text-gray-500 font-mono">
                            {t("modal.withdraw.cryptoDescription")}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Details Input */}
                  <div>
                    <label className="text-[10px] text-gray-500 font-mono uppercase mb-2 block">
                      {t("modal.withdraw.walletAddress")}
                    </label>
                    <input
                      type="text"
                      value={withdrawDetails}
                      onChange={(e) => setWithdrawDetails(e.target.value)}
                      placeholder={t("modal.withdraw.walletPlaceholder")}
                      className="w-full bg-black border border-white/20 focus:border-purple-500 px-4 py-3 text-white font-mono outline-none transition-colors"
                    />
                  </div>
                </div>
              )}

              {/* Confirm/Alert Content */}
              {(state.type === "confirm" || state.type === "alert") && state.message && (
                <p className="text-gray-300 text-sm leading-relaxed">{state.message}</p>
              )}

              {/* Prompt Content */}
              {state.type === "prompt" && (
                <input
                  type={state.inputType || "text"}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={state.placeholder}
                  className="w-full bg-black border border-white/20 focus:border-pandora-cyan px-4 py-3 text-white font-mono outline-none transition-colors"
                  autoFocus
                />
              )}

              {/* Error */}
              {error && (
                <div className="mt-3 px-3 py-2 bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono">
                  ⚠ {error}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-6 pb-6 pt-2 flex gap-3">
              {state.type !== "alert" && (
                <button
                  onClick={onClose}
                  className="flex-1 py-3 bg-white/5 border border-white/10 text-gray-400 text-xs font-bold uppercase tracking-wider hover:bg-white/10 hover:text-white transition-colors"
                >
                  {t("modal.cancel")}
                </button>
              )}
              <button
                onClick={handleSubmit}
                disabled={state.isLoading}
                className={`flex-1 py-3 text-xs font-bold uppercase tracking-wider transition-colors flex items-center justify-center gap-2 ${getButtonClassName(state.type, state.icon)}`}
              >
                {state.isLoading ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <>
                    {state.type === "topup" && <Plus size={14} />}
                    {state.type === "withdraw" && <ArrowUpRight size={14} />}
                    {getButtonText(state.type, t)}
                  </>
                )}
              </button>
            </div>

            {/* Scanline effect */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.1)_50%)] bg-[length:100%_4px] opacity-20" />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// ==================== PROVIDER ====================

export const CyberModalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [modalState, setModalState] = useState<ModalState>({
    isOpen: false,
    type: "alert",
    title: "",
  });

  const hideModal = useCallback(() => {
    setModalState((prev) => ({ ...prev, isOpen: false }));
  }, []);

  const showModal = useCallback((config: ModalConfig) => {
    setModalState({
      ...config,
      isOpen: true,
      isLoading: false,
    });
  }, []);

  const showTopUp = useCallback(
    (config: {
      currency: string;
      balance: number;
      minAmount: number;
      onConfirm: (amount: number) => Promise<void>;
    }) => {
      setModalState({
        type: "topup",
        title: "TOP UP BALANCE",
        icon: "wallet",
        currency: config.currency,
        balance: config.balance,
        minAmount: config.minAmount,
        inputType: "number",
        onConfirm: config.onConfirm,
        isOpen: true,
        isLoading: false,
      });
    },
    []
  );

  const showWithdraw = useCallback(
    (config: {
      currency: string;
      balance: number;
      minAmount: number;
      maxAmount?: number;
      previewWithdrawal?: (amount: number) => Promise<{
        amount_requested: number;
        amount_usdt_gross: number;
        network_fee: number;
        amount_usdt_net: number;
        can_withdraw: boolean;
      }>;
      onConfirm: (amount: number, method: string, details: string) => Promise<void>;
    }) => {
      setModalState({
        type: "withdraw",
        title: "WITHDRAW FUNDS",
        icon: "withdraw",
        currency: config.currency,
        balance: config.balance,
        minAmount: config.minAmount,
        maxAmount: config.maxAmount || config.balance,
        inputType: "number",
        onConfirm: config.onConfirm,
        previewWithdrawal: config.previewWithdrawal,
        isOpen: true,
        isLoading: false,
      });
    },
    []
  );

  const showConfirm = useCallback((title: string, message: string, onConfirm: () => void) => {
    setModalState({
      type: "confirm",
      title,
      message,
      icon: "warning",
      onConfirm,
      isOpen: true,
      isLoading: false,
    });
  }, []);

  const showAlert = useCallback(
    (title: string, message: string, icon: "warning" | "success" | "info" = "info") => {
      setModalState({
        type: "alert",
        title,
        message,
        icon,
        isOpen: true,
        isLoading: false,
      });
    },
    []
  );

  const handleSubmit = async (value?: ModalSubmitValue) => {
    if (modalState.onConfirm) {
      setModalState((prev) => ({ ...prev, isLoading: true }));
      try {
        if (
          modalState.type === "withdraw" &&
          value &&
          typeof value === "object" &&
          "amount" in value
        ) {
          await (
            modalState.onConfirm as (
              amount: number,
              method: string,
              details: string
            ) => Promise<void>
          )(value.amount, value.method, value.details);
        } else {
          await (modalState.onConfirm as (value?: string | number) => void | Promise<void>)(
            value as string | number | undefined
          );
        }
        hideModal();
      } catch (error: unknown) {
        // Show error but keep modal open
        const errorMessage = error instanceof Error ? error.message : "Operation failed";
        setModalState((prev) => ({
          ...prev,
          isLoading: false,
          message: errorMessage,
        }));
      }
    } else {
      hideModal();
    }
  };

  return (
    <CyberModalContext.Provider
      value={{ showModal, hideModal, showTopUp, showWithdraw, showConfirm, showAlert }}
    >
      {children}
      <Modal state={modalState} onClose={hideModal} onSubmit={handleSubmit} />
    </CyberModalContext.Provider>
  );
};

export default CyberModalProvider;
