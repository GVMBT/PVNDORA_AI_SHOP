/**
 * CyberModal - Unified cyberpunk-style modal system
 *
 * Replaces native window.prompt, alert, and confirm dialogs
 * with styled modals matching PVNDORA aesthetic.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle,
  Info,
  Loader2,
  Plus,
  Wallet,
  X,
} from "lucide-react";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useLocaleContext } from "../../contexts/LocaleContext";
import { useLocale } from "../../hooks/useLocale";
import { getCurrencySymbol } from "../../utils/currency";

// Helper functions for button styling (avoid nested ternaries)
const getButtonClassName = (type: string, icon?: string): string => {
  if (type === "withdraw") {
    return "bg-purple-500 hover:bg-purple-400 text-white";
  }
  if (type === "alert" && icon === "warning") {
    return "bg-orange-500 hover:bg-orange-400 text-white";
  }
  return "bg-pandora-cyan hover:bg-white text-black";
};

const getButtonText = (type: string, t: (key: string) => string): string => {
  if (type === "topup") {
    return t("modal.topUp.button");
  }
  if (type === "withdraw") {
    return t("modal.withdraw.button");
  }
  if (type === "alert") {
    return t("modal.ok");
  }
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

  // Helper to validate amount (reduces cognitive complexity)
  const validateAmount = (amount: number): string | null => {
    if (Number.isNaN(amount) || amount <= 0) {
      return t("modal.errors.enterAmount");
    }
    if (state.minAmount && amount < state.minAmount) {
      return `${t("modal.errors.minAmount")}: ${state.minAmount} ${state.currency}`;
    }
    if (state.maxAmount && amount > state.maxAmount) {
      return `${t("modal.errors.maxAmount")}: ${state.maxAmount} ${state.currency}`;
    }
    return null;
  };

  // Helper to validate withdrawal (reduces cognitive complexity)
  const validateWithdrawal = (amount: number): string | null => {
    if ((state.balance ?? 0) > 0 && amount > (state.balance ?? 0)) {
      return t("modal.errors.insufficientFunds");
    }
    if (withdrawPreview && !withdrawPreview.can_withdraw) {
      return "Сумма слишком мала. После комиссии вы получите менее 8.5 USDT (требование биржи: минимум 10 USD).";
    }
    if (!withdrawDetails?.trim()) {
      return t("modal.errors.enterDetails");
    }
    return null;
  };

  // Helper to prepare submit data (reduces cognitive complexity)
  const prepareSubmitData = () => {
    if (state.type === "withdraw") {
      return {
        amount: Number.parseFloat(inputValue),
        method: withdrawMethod,
        details: withdrawDetails,
      };
    }
    if (state.type === "topup" || state.type === "prompt") {
      return state.inputType === "number" ? Number.parseFloat(inputValue) : inputValue;
    }
    return undefined;
  };

  const handleSubmit = () => {
    // Validate for topup/withdraw
    if (state.type === "topup" || state.type === "withdraw") {
      const amount = Number.parseFloat(inputValue);
      const amountError = validateAmount(amount);
      if (amountError) {
        setError(amountError);
        return;
      }

      if (state.type === "withdraw") {
        const withdrawError = validateWithdrawal(amount);
        if (withdrawError) {
          setError(withdrawError);
          return;
        }
      }
    }

    setError(null);
    onSubmit(prepareSubmitData());
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
          animate={{ opacity: 1 }}
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
          onClick={onClose}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

          {/* Modal */}
          <motion.div
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="relative w-full max-w-md overflow-hidden border border-white/10 bg-[#0a0a0a] shadow-2xl"
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            onClick={(e) => e.stopPropagation()}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
          >
            {/* Corner decorations */}
            <div className="absolute top-0 left-0 h-4 w-4 border-pandora-cyan border-t-2 border-l-2" />
            <div className="absolute top-0 right-0 h-4 w-4 border-pandora-cyan border-t-2 border-r-2" />
            <div className="absolute bottom-0 left-0 h-4 w-4 border-pandora-cyan border-b-2 border-l-2" />
            <div className="absolute right-0 bottom-0 h-4 w-4 border-pandora-cyan border-r-2 border-b-2" />

            {/* Glow effect */}
            <div className="pointer-events-none absolute -top-20 left-1/2 h-40 w-40 -translate-x-1/2 bg-pandora-cyan/10 blur-3xl" />

            {/* Header */}
            <div className="relative border-white/5 border-b px-6 pt-6 pb-4">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-white/10 bg-white/5">
                  {getIcon()}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold font-display text-lg text-white uppercase tracking-wider">
                    {state.title}
                  </h3>
                  {/* Show message in header only for non-alert/confirm types (like prompt) */}
                  {state.message && state.type !== "alert" && state.type !== "confirm" && (
                    <p className="mt-1 font-mono text-gray-500 text-xs">{state.message}</p>
                  )}
                </div>
                <button
                  className="flex h-8 w-8 items-center justify-center rounded text-gray-500 transition-colors hover:bg-white/10 hover:text-white"
                  onClick={onClose}
                  type="button"
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
                  <div className="rounded border border-white/10 bg-white/5 p-4">
                    <div className="mb-1 font-mono text-[10px] text-gray-500 uppercase">
                      {t("modal.topUp.currentBalance")}
                    </div>
                    <div className="font-bold font-display text-2xl text-pandora-cyan">
                      {state.balance?.toLocaleString()} {currencySymbol}
                    </div>
                  </div>

                  {/* Amount Input */}
                  <div>
                    <label
                      className="mb-2 block font-mono text-[10px] text-gray-500 uppercase"
                      htmlFor="topup-amount"
                    >
                      {t("modal.topUp.amount")}
                    </label>
                    <div className="relative">
                      <input
                        className="w-full border border-white/20 bg-black px-4 py-3 font-mono text-lg text-white outline-none transition-colors focus:border-pandora-cyan"
                        id="topup-amount"
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={`Min: ${state.minAmount}`}
                        type="number"
                        value={inputValue}
                      />
                      <span className="absolute top-1/2 right-4 -translate-y-1/2 font-mono text-gray-500">
                        {currencySymbol}
                      </span>
                    </div>
                  </div>

                  {/* Quick amounts */}
                  <div className="flex gap-2">
                    {getPresetAmounts.map((amount) => (
                      <button
                        className={`flex-1 border py-2 font-mono text-xs transition-colors ${
                          inputValue === String(amount)
                            ? "border-pandora-cyan bg-pandora-cyan/20 text-pandora-cyan"
                            : "border-white/10 bg-white/5 text-gray-400 hover:border-white/30"
                        }`}
                        key={amount}
                        onClick={() => setInputValue(String(amount))}
                        type="button"
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
                  <div className="rounded border border-white/10 bg-white/5 p-4">
                    <div className="mb-1 font-mono text-[10px] text-gray-500 uppercase">
                      {t("modal.withdraw.availableBalance")}
                    </div>
                    <div className="font-bold font-display text-2xl text-green-500">
                      {state.balance?.toLocaleString()} {currencySymbol}
                    </div>
                  </div>

                  {/* Amount Input */}
                  <div>
                    <div className="mb-2 flex items-center justify-between">
                      <label
                        className="font-mono text-[10px] text-gray-500 uppercase"
                        htmlFor="withdraw-amount"
                      >
                        {t("modal.withdraw.amount")}
                      </label>
                      {state.maxAmount && state.maxAmount > 0 && (
                        <button
                          className="font-mono text-[10px] text-purple-400 uppercase transition-colors hover:text-purple-300"
                          onClick={() => {
                            setInputValue(state.maxAmount?.toString());
                          }}
                          type="button"
                        >
                          {t("modal.withdraw.max") || "МАКС"}
                        </button>
                      )}
                    </div>
                    <div className="relative">
                      <input
                        className="w-full border border-white/20 bg-black px-4 py-3 pr-16 font-mono text-lg text-white outline-none transition-colors focus:border-purple-500"
                        id="withdraw-amount"
                        max={state.maxAmount || state.balance}
                        min={state.minAmount}
                        onChange={(e) => setInputValue(e.target.value)}
                        placeholder={`Min: ${state.minAmount}`}
                        type="number"
                        value={inputValue}
                      />
                      <span className="absolute top-1/2 right-4 -translate-y-1/2 font-mono text-gray-500">
                        {currencySymbol}
                      </span>
                    </div>
                  </div>

                  {/* Withdrawal Preview (Fees and Final Amount) */}
                  {state.type === "withdraw" &&
                    withdrawPreview &&
                    !loadingPreview &&
                    Number.parseFloat(inputValue) > 0 && (
                      <div className="space-y-2 rounded border border-white/10 bg-white/5 p-4">
                        <div className="mb-2 font-mono text-[10px] text-gray-500 uppercase">
                          {t("modal.withdraw.preview") || "РАСЧЁТ ВЫВОДА"}
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="font-mono text-gray-400">Сумма (USDT):</span>
                          <span className="font-bold font-mono text-white">
                            {withdrawPreview.amount_usdt_gross.toFixed(2)} USDT
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="font-mono text-gray-400">Комиссия сети:</span>
                          <span className="font-mono text-orange-400">
                            -{withdrawPreview.network_fee.toFixed(2)} USDT
                          </span>
                        </div>
                        <div className="mt-2 flex justify-between border-white/10 border-t pt-2">
                          <span className="font-bold font-mono text-gray-300">К получению:</span>
                          <span className="font-bold font-mono text-green-400 text-lg">
                            {withdrawPreview.amount_usdt_net.toFixed(2)} USDT
                          </span>
                        </div>
                        {!withdrawPreview.can_withdraw && (
                          <div className="mt-2 border border-orange-500/30 bg-orange-500/10 px-2 py-1 font-mono text-orange-400 text-xs">
                            ⚠ После комиссии сумма слишком мала. Минимум: 8.5 USDT (требование
                            биржи: 10 USD)
                          </div>
                        )}
                      </div>
                    )}
                  {state.type === "withdraw" && loadingPreview && (
                    <div className="rounded border border-white/10 bg-white/5 p-4 text-center">
                      <Loader2 className="mx-auto animate-spin text-purple-400" size={16} />
                    </div>
                  )}

                  {/* Method Selection - Only Crypto (TRC20 USDT) */}
                  <div>
                    <div className="mb-2 block font-mono text-[10px] text-gray-500 uppercase">
                      {t("modal.withdraw.method")}
                    </div>
                    <div className="rounded border border-purple-500 bg-purple-500/20 p-4">
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">₿</span>
                        <div>
                          <div className="font-bold font-mono text-purple-400 text-sm">
                            TRC20 USDT
                          </div>
                          <div className="font-mono text-[10px] text-gray-500">
                            {t("modal.withdraw.cryptoDescription")}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Details Input */}
                  <div>
                    <label
                      className="mb-2 block font-mono text-[10px] text-gray-500 uppercase"
                      htmlFor="withdraw-wallet"
                    >
                      {t("modal.withdraw.walletAddress")}
                    </label>
                    <input
                      className="w-full border border-white/20 bg-black px-4 py-3 font-mono text-white outline-none transition-colors focus:border-purple-500"
                      id="withdraw-wallet"
                      onChange={(e) => setWithdrawDetails(e.target.value)}
                      placeholder={t("modal.withdraw.walletPlaceholder")}
                      type="text"
                      value={withdrawDetails}
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
                  className="w-full border border-white/20 bg-black px-4 py-3 font-mono text-white outline-none transition-colors focus:border-pandora-cyan"
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={state.placeholder}
                  type={state.inputType || "text"}
                  value={inputValue}
                />
              )}

              {/* Error */}
              {error && (
                <div className="mt-3 border border-red-500/30 bg-red-500/10 px-3 py-2 font-mono text-red-400 text-xs">
                  ⚠ {error}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex gap-3 px-6 pt-2 pb-6">
              {state.type !== "alert" && (
                <button
                  className="flex-1 border border-white/10 bg-white/5 py-3 font-bold text-gray-400 text-xs uppercase tracking-wider transition-colors hover:bg-white/10 hover:text-white"
                  onClick={onClose}
                  type="button"
                >
                  {t("modal.cancel")}
                </button>
              )}
              <button
                className={`flex flex-1 items-center justify-center gap-2 py-3 font-bold text-xs uppercase tracking-wider transition-colors ${getButtonClassName(state.type, state.icon)}`}
                disabled={state.isLoading}
                onClick={handleSubmit}
                type="button"
              >
                {state.isLoading ? (
                  <Loader2 className="animate-spin" size={16} />
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
            <div className="pointer-events-none absolute inset-0 bg-[length:100%_4px] bg-[linear-gradient(transparent_50%,rgba(0,0,0,0.1)_50%)] opacity-20" />
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

  // Memoize context value to prevent unnecessary rerenders (S6481)
  const contextValue = React.useMemo(
    () => ({ showModal, hideModal, showTopUp, showWithdraw, showConfirm, showAlert }),
    [showModal, hideModal, showTopUp, showWithdraw, showConfirm, showAlert]
  );

  return (
    <CyberModalContext.Provider value={contextValue}>
      {children}
      <Modal onClose={hideModal} onSubmit={handleSubmit} state={modalState} />
    </CyberModalContext.Provider>
  );
};

export default CyberModalProvider;
