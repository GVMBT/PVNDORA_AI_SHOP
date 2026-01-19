/**
 * ProfileStats Component
 *
 * Displays balance card, referral link generator, and stats overview.
 */

import {
  ArrowUpRight,
  Check,
  Copy,
  Network,
  Percent,
  Plus,
  QrCode,
  RefreshCw,
  Settings,
  Share2,
  Wallet,
  X,
} from "lucide-react";
import type React from "react";
import { memo, useCallback } from "react";
import { useLocaleContext } from "../../contexts/LocaleContext";
import { useLocale } from "../../hooks/useLocale";
import { getCurrencySymbol } from "../../utils/currency";
import { logger } from "../../utils/logger";
import DecryptedText from "./DecryptedText";
import type { ProfileDataProp } from "./types";

// Format balance for display (remove excessive decimals)
function formatBalance(balance: string | number, currency: string): string {
  const num = typeof balance === "string" ? Number.parseFloat(balance) : balance;
  if (Number.isNaN(num)) return "0";

  // Integer currencies (no decimals)
  const integerCurrencies = ["RUB", "UAH", "TRY", "INR"];
  const isInteger = integerCurrencies.includes(currency.toUpperCase());

  if (isInteger) {
    return Math.round(num).toLocaleString("en-US", { maximumFractionDigits: 0 });
  }

  // For USD/EUR/etc: show max 2 decimal places
  return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

interface ProfileStatsProps {
  user: ProfileDataProp;
  copied: boolean;
  rewardMode: "cash" | "discount";
  onHaptic?: (type?: "light" | "medium") => void;
  onTopUp?: () => void;
  onWithdraw?: () => void;
  onCopy: () => void;
  onShare: () => void;
  onToggleRewardMode: () => void;
  onUpdatePreferences?: (
    preferred_currency?: string,
    interface_language?: string
  ) => Promise<{ success: boolean; message: string }>;
  onCancelWithdrawal?: (withdrawalId: string) => Promise<void>;
}

const ProfileStats: React.FC<ProfileStatsProps> = ({
  user,
  copied,
  rewardMode,
  onHaptic,
  onTopUp,
  onWithdraw,
  onCopy,
  onShare,
  onToggleRewardMode,
  onUpdatePreferences,
  onCancelWithdrawal,
}) => {
  // Use currency and locale from context for active state (updates immediately on user action)
  const { locale: contextLocale } = useLocaleContext();
  const { t } = useLocale();
  // After RUB-only migration, currency is always RUB
  const activeCurrency = "RUB";

  const handleLanguageChange = useCallback(
    async (lang: "ru" | "en") => {
      if (onHaptic) onHaptic("light");
      if (onUpdatePreferences) {
        try {
          await onUpdatePreferences(undefined, lang);
          if (onHaptic) onHaptic("light");
          // No reload needed - context will update automatically
        } catch (err) {
          // Error handled by logger - rethrow to allow parent to handle
          logger.error("Error changing language", err);
          throw err;
        }
      }
    },
    [onHaptic, onUpdatePreferences]
  );

  return (
    <div className="mb-12 grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Internal Balance Card */}
      <div className="flex flex-col lg:col-span-4">
        <div className="group relative flex h-full flex-col justify-between overflow-hidden border border-white/10 bg-[#080808] p-6 transition-all hover:border-pandora-cyan/30">
          <div className="absolute top-0 right-0 p-4 opacity-50 transition-opacity group-hover:opacity-100">
            <Wallet className="text-pandora-cyan" size={24} />
          </div>
          <div className="absolute bottom-0 left-0 h-1 w-full origin-left scale-x-0 bg-gradient-to-r from-pandora-cyan/50 to-transparent transition-transform duration-500 group-hover:scale-x-100" />

          <div className="mb-6">
            <div className="mb-2 flex items-center gap-2 font-mono text-[10px] text-gray-500 uppercase tracking-widest">
              {t("profile.internalBalance")}{" "}
              <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
            </div>
            <div className="flex items-baseline gap-2 font-bold font-display text-4xl text-white sm:text-5xl">
              <DecryptedText text={formatBalance(user.balance, activeCurrency)} />
              <span className="text-pandora-cyan text-xl">{getCurrencySymbol(activeCurrency)}</span>
            </div>

            {/* Reserved Balance (Pending Withdrawals) */}
            {user.pendingWithdrawals && user.pendingWithdrawals.length > 0 && (
              <div className="mt-4 border-white/10 border-t pt-4">
                <div className="mb-2 font-mono text-[10px] text-yellow-500 uppercase tracking-widest">
                  {t("profile.reservedBalance") || "ЗАРЕЗЕРВИРОВАНО"}
                </div>
                {user.pendingWithdrawals.map((w) => {
                  const reservedAmount = w.amount_debited || 0;
                  const reservedCurrency = w.balance_currency || "RUB";
                  return (
                    <div
                      className="mb-2 flex items-center justify-between rounded-sm border border-yellow-500/20 bg-yellow-500/10 p-3 last:mb-0"
                      key={w.id}
                    >
                      <div className="flex flex-col">
                        <div className="flex items-baseline gap-1 font-bold text-sm text-yellow-400">
                          {formatBalance(reservedAmount, reservedCurrency)}
                          <span className="text-xs text-yellow-500">
                            {getCurrencySymbol(reservedCurrency)}
                          </span>
                        </div>
                        <div className="mt-1 text-[10px] text-gray-400">
                          {t("profile.withdraw.pending") || "Ожидает вывода"} •{" "}
                          {w.amount_to_pay ? `${w.amount_to_pay} USDT` : ""}
                        </div>
                      </div>
                      {onCancelWithdrawal && (
                        <button
                          className="ml-3 rounded p-1.5 text-yellow-400 transition-colors hover:bg-yellow-500/20 hover:text-yellow-300"
                          onClick={async () => {
                            if (onHaptic) onHaptic("light");
                            try {
                              await onCancelWithdrawal(w.id);
                            } catch (err) {
                              logger.error("Failed to cancel withdrawal", err);
                            }
                          }}
                          title={t("profile.withdraw.cancel") || "Отменить вывод"}
                          type="button"
                        >
                          <X size={16} />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="mt-auto grid grid-cols-2 gap-3">
            <button
              className="flex items-center justify-center gap-2 rounded-sm border border-white/10 bg-white/5 py-3 font-bold text-white text-xs uppercase tracking-wider transition-colors hover:border-pandora-cyan hover:text-pandora-cyan"
              onClick={() => {
                if (onHaptic) onHaptic("light");
                if (onTopUp) onTopUp();
              }}
              type="button"
            >
              <Plus size={14} /> {t("profile.actions.topUp")}
            </button>
            <button
              className="flex items-center justify-center gap-2 rounded-sm bg-pandora-cyan py-3 font-bold text-black text-xs uppercase tracking-wider shadow-[0_0_15px_rgba(0,255,255,0.2)] transition-colors hover:bg-white"
              onClick={() => {
                if (onHaptic) onHaptic("medium");
                if (onWithdraw) onWithdraw();
              }}
              type="button"
            >
              <ArrowUpRight size={14} /> {t("profile.actions.withdraw")}
            </button>
          </div>
        </div>
      </div>

      {/* Referral Link & Uplink Generator */}
      <div className="flex flex-col lg:col-span-8">
        <div className="group relative flex h-full flex-col justify-between border border-white/10 bg-[#0a0a0a] p-6 transition-all hover:border-pandora-cyan/30">
          {/* Header */}
          <div className="mb-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h3 className="mb-1 flex items-center gap-2 font-bold text-sm text-white">
                <Network className="text-pandora-cyan" size={16} />{" "}
                {t("profile.uplink.title").toUpperCase()}
              </h3>
              <p className="font-mono text-[10px] text-gray-500">{t("profile.uplink.subtitle")}</p>
            </div>

            {/* Stats Summary */}
            <div className="flex w-full items-center justify-between gap-6 rounded-sm border border-white/5 bg-white/5 px-4 py-2 font-mono text-[10px] sm:w-auto sm:justify-start">
              <div className="flex flex-col items-center sm:items-start">
                <span className="text-gray-500">{t("profile.stats.clicks").toUpperCase()}</span>
                <span className="font-bold text-base text-white">{user.stats.clicks}</span>
              </div>
              <div className="h-6 w-px bg-white/10" />
              <div className="flex flex-col items-center sm:items-start">
                <span className="text-gray-500">{t("profile.stats.conversion").toUpperCase()}</span>
                <span className="font-bold text-base text-pandora-cyan">
                  {user.stats.conversion}%
                </span>
              </div>
            </div>
          </div>

          {/* Invite Card / Access Key */}
          <div className="flex flex-col items-stretch gap-4 md:flex-row">
            {/* Visual Access Card */}
            <div className="relative flex min-h-[100px] flex-1 flex-col justify-center overflow-hidden border border-white/20 bg-black p-4">
              {/* Card Background Fx */}
              <div
                className="absolute inset-0 opacity-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                }}
              />
              <div className="absolute top-0 right-0 p-2 opacity-50">
                <QrCode className="text-white" size={32} />
              </div>

              <div className="relative z-10">
                <div className="mb-1 font-mono text-[9px] text-pandora-cyan uppercase tracking-widest">
                  {t("profile.uplink.accessToken")}
                </div>
                <code className="break-all font-bold font-mono text-lg text-white tracking-widest">
                  {user.referralLink.split("/").pop()}
                </code>
              </div>
            </div>

            {/* Actions */}
            <div className="flex w-full flex-col gap-2 md:w-48">
              <button
                className="group/btn relative flex flex-1 items-center justify-center gap-2 overflow-hidden rounded-sm bg-pandora-cyan py-3 font-bold text-black uppercase tracking-widest shadow-[0_0_15px_rgba(0,255,255,0.3)] transition-all hover:bg-white"
                onClick={onShare}
                type="button"
              >
                <span className="relative z-10 flex items-center gap-2">
                  <Share2 size={16} /> {t("profile.actions.shareKey")}
                </span>
                <div className="absolute inset-0 translate-y-full bg-white/50 transition-transform duration-300 group-hover/btn:translate-y-0" />
              </button>

              <button
                className="flex flex-1 items-center justify-center gap-2 rounded-sm border border-white/10 bg-white/5 font-mono text-white text-xs uppercase tracking-widest transition-colors hover:bg-white/10"
                onClick={onCopy}
                type="button"
              >
                {copied ? (
                  <>
                    <Check size={14} /> {t("profile.actions.copied")}
                  </>
                ) : (
                  <>
                    <Copy size={14} /> {t("profile.actions.copyLink")}
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Reward Toggle - VIP only */}
          {user.isVip && (
            <div className="mt-4 flex items-center justify-between border-white/5 border-t pt-3 font-mono text-[10px] text-gray-500">
              <span>{t("profile.uplink.rewardPreference").toUpperCase()}:</span>
              <button
                className={`flex items-center gap-2 rounded-sm border px-3 py-1 font-bold transition-colors ${
                  rewardMode === "cash"
                    ? "border-green-500 bg-green-500/10 text-green-500"
                    : "border-purple-500 bg-purple-500/10 text-purple-500"
                }`}
                onClick={onToggleRewardMode}
                type="button"
              >
                {rewardMode === "cash" ? (
                  <>
                    <Wallet size={12} /> {t("profile.uplink.cashOut").toUpperCase()}
                  </>
                ) : (
                  <>
                    <Percent size={12} /> {t("profile.uplink.discount").toUpperCase()}
                  </>
                )}
                <RefreshCw className="ml-1 opacity-50" size={12} />
              </button>
            </div>
          )}

          {/* Language Settings (Currency removed after RUB-only migration) */}
          {onUpdatePreferences && (
            <div className="mt-4 border-white/5 border-t pt-4">
              <div className="mb-3 flex items-center gap-2 font-mono text-[10px] text-gray-500 uppercase">
                <Settings size={12} /> {t("profile.settings.title")}
              </div>
              <div className="flex flex-wrap items-center gap-4">
                {/* Language Toggle */}
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[9px] text-gray-600">
                    {t("profile.settings.language")}:
                  </span>
                  <div className="flex overflow-hidden rounded-sm border border-white/10 bg-black/50">
                    <button
                      className={`px-3 py-1.5 font-bold font-mono text-[10px] transition-all ${
                        contextLocale === "ru"
                          ? "bg-pandora-cyan text-black"
                          : "text-gray-500 hover:bg-white/5 hover:text-white"
                      }`}
                      onClick={() => handleLanguageChange("ru")}
                      type="button"
                    >
                      RU
                    </button>
                    <button
                      className={`px-3 py-1.5 font-bold font-mono text-[10px] transition-all ${
                        contextLocale === "en"
                          ? "bg-pandora-cyan text-black"
                          : "text-gray-500 hover:bg-white/5 hover:text-white"
                      }`}
                      onClick={() => handleLanguageChange("en")}
                      type="button"
                    >
                      EN
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ProfileStats);
