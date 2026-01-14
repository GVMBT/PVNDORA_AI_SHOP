/**
 * ProfileBilling Component
 *
 * Displays billing logs and transaction history with localization and currency conversion.
 */

import { ArrowDownLeft, ArrowUpRight, Clock, History } from "lucide-react";
import type React from "react";
import { memo, useMemo } from "react";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";
import type { BillingLogData } from "./types";

// Helper for log badge styling (avoid nested ternary)
const getLogBadgeClasses = (isIncome: boolean, type: string): string => {
  if (isIncome) return "text-green-500 border-green-500/20 bg-green-500/5";
  if (type === "OUTCOME") return "text-pandora-cyan border-pandora-cyan/20 bg-pandora-cyan/5";
  return "text-gray-500 border-white/10 bg-white/5";
};

interface ProfileBillingProps {
  logs: BillingLogData[];
  currency?: string;
  exchangeRate?: number;
}

const ProfileBilling: React.FC<ProfileBillingProps> = ({
  logs,
  currency = "USD",
  exchangeRate = 1,
}) => {
  const { t } = useLocale();

  // Format and localize logs
  const localizedLogs = useMemo(() => {
    return logs.map((log) => {
      // Parse transaction type from source for localization
      const sourceKey = log.transactionType?.toLowerCase() || "system";
      const localizedSource = t(`profile.billing.transaction.${sourceKey}`) || log.source;

      // Parse amount (remove sign, convert)
      const amountNum = Number.parseFloat(log.amount.replaceAll(/[+\-,]/g, "")) || 0;
      const isIncome = log.type === "INCOME";

      // Only convert if transaction currency differs from display currency
      // balance_transactions already come in user's balance_currency
      const txCurrency = log.currency;
      const needsConversion = txCurrency && txCurrency !== currency;
      const convertedAmount = needsConversion ? amountNum * exchangeRate : amountNum;
      const formattedAmount = `${isIncome ? "+" : "-"}${formatPrice(convertedAmount, currency)}`;

      return {
        ...log,
        localizedSource,
        formattedAmount,
        isIncome,
      };
    });
  }, [logs, t, currency, exchangeRate]);

  // Localized type labels
  const typeLabels: Record<string, string> = {
    INCOME: t("profile.billing.transaction.income"),
    OUTCOME: t("profile.billing.transaction.outcome"),
    SYSTEM: t("profile.billing.transaction.system"),
  };

  return (
    <div className="border border-white/10 bg-[#050505] overflow-hidden">
      {/* Header */}
      <div className="bg-[#0a0a0a] border-b border-white/10 p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History size={14} className="text-pandora-cyan" />
          <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-white/90">
            {t("profile.billing.title")}
          </div>
        </div>
        <div className="text-[9px] font-mono text-gray-500 uppercase">
          {localizedLogs.length} LOGS DETECTED
        </div>
      </div>

      <div className="p-0 font-mono text-xs">
        {localizedLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-gray-600">
            <div className="w-12 h-12 rounded-full border border-white/5 flex items-center justify-center mb-4">
              <History size={20} className="opacity-20" />
            </div>
            <span className="uppercase tracking-[0.2em] text-[9px] font-bold">
              {t("profile.billing.noTransactions")}
            </span>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {/* Desktop Header Row (Hidden on Mobile) */}
            <div className="hidden sm:grid grid-cols-12 gap-4 px-6 py-3 bg-white/[0.02] border-b border-white/5 text-[9px] font-bold text-gray-500 uppercase tracking-wider">
              <div className="col-span-2 flex items-center gap-2">ID // Type</div>
              <div className="col-span-5">Source / Activity</div>
              <div className="col-span-3 text-right">Amount</div>
              <div className="col-span-2 text-right">Timestamp</div>
            </div>

            {localizedLogs.map((log) => (
              <div
                key={log.id}
                className="group px-4 sm:px-6 py-4 sm:py-3 hover:bg-white/[0.03] transition-all duration-200 relative overflow-hidden"
              >
                {/* Visual indicator bar */}
                <div
                  className={`absolute left-0 top-0 bottom-0 w-[2px] transition-all duration-300 ${
                    log.isIncome
                      ? "bg-green-500/0 group-hover:bg-green-500/50"
                      : "bg-pandora-cyan/0 group-hover:bg-pandora-cyan/50"
                  }`}
                />

                {/* Desktop View */}
                <div className="hidden sm:grid grid-cols-12 gap-4 items-center">
                  {/* ID & Type */}
                  <div className="col-span-2 flex items-center gap-3">
                    <div
                      className={`p-2 rounded-sm ${
                        log.isIncome ? "bg-green-500/10 text-green-500" : "bg-white/5 text-gray-400"
                      }`}
                    >
                      {log.isIncome ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-gray-600 text-[9px] leading-none uppercase tracking-tighter">
                        #{log.id}
                      </span>
                      <span
                        className={`text-[10px] font-bold ${
                          log.isIncome ? "text-green-500/80" : "text-pandora-cyan/80"
                        }`}
                      >
                        {typeLabels[log.type] || log.type}
                      </span>
                    </div>
                  </div>

                  {/* Source */}
                  <div className="col-span-5 flex flex-col">
                    <span className="text-white font-bold text-sm tracking-tight group-hover:text-pandora-cyan transition-colors truncate">
                      {log.localizedSource}
                    </span>
                    <span className="text-[10px] text-gray-500 uppercase tracking-widest opacity-50">
                      Network Transmission
                    </span>
                  </div>

                  {/* Amount */}
                  <div className="col-span-3 text-right flex flex-col items-end">
                    <span
                      className={`text-base font-bold ${
                        log.isIncome ? "text-green-400" : "text-white"
                      }`}
                    >
                      {log.formattedAmount}
                    </span>
                  </div>

                  {/* Date */}
                  <div className="col-span-2 text-right flex flex-col items-end justify-center">
                    <div className="flex items-center gap-1.5 text-gray-500 group-hover:text-gray-400 transition-colors">
                      <Clock size={10} />
                      <span className="text-[10px]">{log.date}</span>
                    </div>
                  </div>
                </div>

                {/* Mobile View */}
                <div className="sm:hidden flex flex-col gap-3">
                  <div className="flex items-start justify-between">
                    <div className="flex gap-3">
                      <div
                        className={`p-2.5 rounded-sm shrink-0 ${
                          log.isIncome
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/5 text-gray-400"
                        }`}
                      >
                        {log.isIncome ? <ArrowUpRight size={16} /> : <ArrowDownLeft size={16} />}
                      </div>
                      <div className="flex flex-col min-w-0">
                        <span className="text-white font-bold text-sm truncate pr-2">
                          {log.localizedSource}
                        </span>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-gray-600 text-[9px] font-mono">#{log.id}</span>
                          <span
                            className={`px-1.5 py-0.5 text-[8px] font-bold border rounded-sm tracking-wider ${getLogBadgeClasses(log.isIncome, log.type)}`}
                          >
                            {typeLabels[log.type] || log.type}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div
                      className={`font-bold text-base shrink-0 ${
                        log.isIncome ? "text-green-400" : "text-white"
                      }`}
                    >
                      {log.formattedAmount}
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t border-white/5 pt-2 mt-1">
                    <div className="flex items-center gap-1.5 text-gray-500 text-[9px] uppercase tracking-widest font-bold opacity-50">
                      Status: Verified
                    </div>
                    <div className="flex items-center gap-1.5 text-gray-500 text-[10px]">
                      <Clock size={10} />
                      <span>{log.date}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(ProfileBilling);
