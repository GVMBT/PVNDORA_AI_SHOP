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
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-12">
      {/* Internal Balance Card */}
      <div className="lg:col-span-4 flex flex-col">
        <div className="bg-[#080808] border border-white/10 p-6 relative overflow-hidden h-full flex flex-col justify-between group hover:border-pandora-cyan/30 transition-all">
          <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
            <Wallet size={24} className="text-pandora-cyan" />
          </div>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-pandora-cyan/50 to-transparent scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left" />

          <div className="mb-6">
            <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 flex items-center gap-2">
              {t("profile.internalBalance")}{" "}
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            </div>
            <div className="text-4xl sm:text-5xl font-display font-bold text-white flex items-baseline gap-2">
              <DecryptedText text={formatBalance(user.balance, activeCurrency)} />
              <span className="text-xl text-pandora-cyan">{getCurrencySymbol(activeCurrency)}</span>
            </div>

            {/* Reserved Balance (Pending Withdrawals) */}
            {user.pendingWithdrawals && user.pendingWithdrawals.length > 0 && (
              <div className="mt-4 pt-4 border-t border-white/10">
                <div className="text-[10px] font-mono text-yellow-500 uppercase tracking-widest mb-2">
                  {t("profile.reservedBalance") || "ЗАРЕЗЕРВИРОВАНО"}
                </div>
                {user.pendingWithdrawals.map((w) => {
                  const reservedAmount = w.amount_debited || 0;
                  const reservedCurrency = w.balance_currency || "RUB";
                  return (
                    <div
                      key={w.id}
                      className="flex items-center justify-between bg-yellow-500/10 border border-yellow-500/20 p-3 rounded-sm mb-2 last:mb-0"
                    >
                      <div className="flex flex-col">
                        <div className="text-sm font-bold text-yellow-400 flex items-baseline gap-1">
                          {formatBalance(reservedAmount, reservedCurrency)}
                          <span className="text-xs text-yellow-500">
                            {getCurrencySymbol(reservedCurrency)}
                          </span>
                        </div>
                        <div className="text-[10px] text-gray-400 mt-1">
                          {t("profile.withdraw.pending") || "Ожидает вывода"} •{" "}
                          {w.amount_to_pay ? `${w.amount_to_pay} USDT` : ""}
                        </div>
                      </div>
                      {onCancelWithdrawal && (
                        <button
                          type="button"
                          onClick={async () => {
                            if (onHaptic) onHaptic("light");
                            try {
                              await onCancelWithdrawal(w.id);
                            } catch (err) {
                              logger.error("Failed to cancel withdrawal", err);
                            }
                          }}
                          className="ml-3 p-1.5 text-yellow-400 hover:text-yellow-300 hover:bg-yellow-500/20 rounded transition-colors"
                          title={t("profile.withdraw.cancel") || "Отменить вывод"}
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

          <div className="grid grid-cols-2 gap-3 mt-auto">
            <button
              type="button"
              onClick={() => {
                if (onHaptic) onHaptic("light");
                if (onTopUp) onTopUp();
              }}
              className="bg-white/5 border border-white/10 hover:border-pandora-cyan text-white hover:text-pandora-cyan font-bold py-3 text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2 rounded-sm"
            >
              <Plus size={14} /> {t("profile.actions.topUp")}
            </button>
            <button
              type="button"
              onClick={() => {
                if (onHaptic) onHaptic("medium");
                if (onWithdraw) onWithdraw();
              }}
              className="bg-pandora-cyan text-black font-bold py-3 text-xs uppercase tracking-wider hover:bg-white transition-colors flex items-center justify-center gap-2 rounded-sm shadow-[0_0_15px_rgba(0,255,255,0.2)]"
            >
              <ArrowUpRight size={14} /> {t("profile.actions.withdraw")}
            </button>
          </div>
        </div>
      </div>

      {/* Referral Link & Uplink Generator */}
      <div className="lg:col-span-8 flex flex-col">
        <div className="bg-[#0a0a0a] border border-white/10 p-6 h-full flex flex-col justify-between relative group hover:border-pandora-cyan/30 transition-all">
          {/* Header */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
                <Network size={16} className="text-pandora-cyan" />{" "}
                {t("profile.uplink.title").toUpperCase()}
              </h3>
              <p className="text-[10px] text-gray-500 font-mono">{t("profile.uplink.subtitle")}</p>
            </div>

            {/* Stats Summary */}
            <div className="flex items-center gap-6 text-[10px] font-mono bg-white/5 px-4 py-2 rounded-sm border border-white/5 w-full sm:w-auto justify-between sm:justify-start">
              <div className="flex flex-col items-center sm:items-start">
                <span className="text-gray-500">{t("profile.stats.clicks").toUpperCase()}</span>
                <span className="text-white font-bold text-base">{user.stats.clicks}</span>
              </div>
              <div className="w-px h-6 bg-white/10" />
              <div className="flex flex-col items-center sm:items-start">
                <span className="text-gray-500">{t("profile.stats.conversion").toUpperCase()}</span>
                <span className="text-pandora-cyan font-bold text-base">
                  {user.stats.conversion}%
                </span>
              </div>
            </div>
          </div>

          {/* Invite Card / Access Key */}
          <div className="flex flex-col md:flex-row gap-4 items-stretch">
            {/* Visual Access Card */}
            <div className="flex-1 bg-black border border-white/20 p-4 relative overflow-hidden flex flex-col justify-center min-h-[100px]">
              {/* Card Background Fx */}
              <div
                className="absolute inset-0 opacity-10"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
                }}
              />
              <div className="absolute top-0 right-0 p-2 opacity-50">
                <QrCode size={32} className="text-white" />
              </div>

              <div className="relative z-10">
                <div className="text-[9px] font-mono text-pandora-cyan mb-1 uppercase tracking-widest">
                  {t("profile.uplink.accessToken")}
                </div>
                <code className="text-lg font-mono text-white font-bold tracking-widest break-all">
                  {user.referralLink.split("/").pop()}
                </code>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2 w-full md:w-48">
              <button
                type="button"
                onClick={onShare}
                className="flex-1 bg-pandora-cyan text-black font-bold py-3 uppercase tracking-widest hover:bg-white transition-all flex items-center justify-center gap-2 rounded-sm shadow-[0_0_15px_rgba(0,255,255,0.3)] relative overflow-hidden group/btn"
              >
                <span className="relative z-10 flex items-center gap-2">
                  <Share2 size={16} /> {t("profile.actions.shareKey")}
                </span>
                <div className="absolute inset-0 bg-white/50 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
              </button>

              <button
                type="button"
                onClick={onCopy}
                className="flex-1 bg-white/5 hover:bg-white/10 text-white font-mono text-xs uppercase tracking-widest transition-colors flex items-center justify-center gap-2 rounded-sm border border-white/10"
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
            <div className="mt-4 flex items-center justify-between text-[10px] font-mono text-gray-500 border-t border-white/5 pt-3">
              <span>{t("profile.uplink.rewardPreference").toUpperCase()}:</span>
              <button
                type="button"
                onClick={onToggleRewardMode}
                className={`flex items-center gap-2 font-bold px-3 py-1 border rounded-sm transition-colors ${
                  rewardMode === "cash"
                    ? "border-green-500 text-green-500 bg-green-500/10"
                    : "border-purple-500 text-purple-500 bg-purple-500/10"
                }`}
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
                <RefreshCw size={12} className="ml-1 opacity-50" />
              </button>
            </div>
          )}

          {/* Language Settings (Currency removed after RUB-only migration) */}
          {onUpdatePreferences && (
            <div className="mt-4 border-t border-white/5 pt-4">
              <div className="text-[10px] font-mono text-gray-500 uppercase mb-3 flex items-center gap-2">
                <Settings size={12} /> {t("profile.settings.title")}
              </div>
              <div className="flex flex-wrap gap-4 items-center">
                {/* Language Toggle */}
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-mono text-gray-600">
                    {t("profile.settings.language")}:
                  </span>
                  <div className="flex bg-black/50 border border-white/10 rounded-sm overflow-hidden">
                    <button
                      type="button"
                      onClick={() => handleLanguageChange("ru")}
                      className={`px-3 py-1.5 text-[10px] font-mono font-bold transition-all ${
                        contextLocale === "ru"
                          ? "bg-pandora-cyan text-black"
                          : "text-gray-500 hover:text-white hover:bg-white/5"
                      }`}
                    >
                      RU
                    </button>
                    <button
                      type="button"
                      onClick={() => handleLanguageChange("en")}
                      className={`px-3 py-1.5 text-[10px] font-mono font-bold transition-all ${
                        contextLocale === "en"
                          ? "bg-pandora-cyan text-black"
                          : "text-gray-500 hover:text-white hover:bg-white/5"
                      }`}
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
