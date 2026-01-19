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
  if (isIncome) {
    return "text-green-500 border-green-500/20 bg-green-500/5";
  }
  if (type === "OUTCOME") {
    return "text-pandora-cyan border-pandora-cyan/20 bg-pandora-cyan/5";
  }
  return "text-gray-500 border-white/10 bg-white/5";
};

// Helper to process metadata and build localized source (reduces cognitive complexity)
type TranslateFunc = (key: string) => string | undefined;
interface MetadataResult {
  source: string;
  details: string;
}

// Helper functions for metadata processing (reduce cognitive complexity)
const processPurchaseMetadata = (meta: BillingLogData["metadata"], t: TranslateFunc): string => {
  if (meta.payment_method === "balance") {
    return t("profile.billing.transaction.purchase_balance") || "Оплата с баланса";
  }
  return t("profile.billing.transaction.purchase_external") || "Оплата заказа";
};

const processBonusMetadata = (
  meta: BillingLogData["metadata"],
  t: TranslateFunc
): { source: string; details: string } => {
  const level = meta.level ? String(meta.level) : "";
  const source = t(`profile.billing.transaction.bonus_l${level}`) || `Реф. бонус L${level}`;
  const details = meta.from_username
    ? `${t("profile.billing.transaction.details.from") || "от"} ${meta.from_username}`
    : "";
  return { source, details };
};

const processRefundMetadata = (
  meta: BillingLogData["metadata"],
  t: TranslateFunc
): { source: string; details: string } => {
  const source = t("profile.billing.transaction.refund_auto") || "Авто-возврат";
  const details = meta.product_name ? String(meta.product_name) : "";
  return { source, details };
};

const processCashbackMetadata = (meta: BillingLogData["metadata"]): string => {
  const percent =
    typeof meta.cashback_percent === "number"
      ? meta.cashback_percent
      : Number.parseFloat(String(meta.cashback_percent)) || 0;
  return `${percent}% кэшбек`;
};

function processMetadata(
  meta: BillingLogData["metadata"],
  sourceKey: string,
  defaultSource: string,
  t: TranslateFunc
): MetadataResult {
  if (!meta) {
    return { source: defaultSource, details: "" };
  }

  // For purchases, show payment method
  if (sourceKey === "purchase" && meta.payment_method) {
    return { source: processPurchaseMetadata(meta, t), details: "" };
  }

  // For referral bonuses, show level and from whom
  if (sourceKey === "bonus" && meta.level) {
    const result = processBonusMetadata(meta, t);
    return { source: result.source, details: result.details };
  }

  // For refunds, show reason
  if (sourceKey === "refund" && meta.refund_type === "auto_expired") {
    const result = processRefundMetadata(meta, t);
    return { source: result.source, details: result.details };
  }

  // For cashback, show percent
  if (sourceKey === "cashback" && meta.cashback_percent) {
    return { source: processCashbackMetadata(meta), details: "" };
  }

  return { source: defaultSource, details: "" };
}

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

  // Format and localize logs with extended info
  const localizedLogs = useMemo(() => {
    return logs.map((log) => {
      const sourceKey = log.transactionType?.toLowerCase() || "system";
      const defaultSource = t(`profile.billing.transaction.${sourceKey}`) || log.source;

      // Process metadata for informative display
      const { source: metaSource, details } = processMetadata(
        log.metadata,
        sourceKey,
        defaultSource,
        t
      );

      // Fallback: use description if source is generic
      let localizedSource = metaSource;
      if (
        (sourceKey === "credit" || sourceKey === "debit") &&
        log.source &&
        log.source !== sourceKey.toUpperCase()
      ) {
        localizedSource = log.source;
      }

      // Parse and convert amount
      const amountNum =
        Number.parseFloat(log.amount.replaceAll("+", "").replaceAll("-", "").replaceAll(",", "")) ||
        0;
      const isIncome = log.type === "INCOME";
      const needsConversion = log.currency && log.currency !== currency;
      const convertedAmount = needsConversion ? amountNum * exchangeRate : amountNum;
      const formattedAmount = `${isIncome ? "+" : "-"}${formatPrice(convertedAmount, currency)}`;

      return { ...log, localizedSource, details, formattedAmount, isIncome };
    });
  }, [logs, t, currency, exchangeRate]);

  // Localized type labels
  const typeLabels: Record<string, string> = {
    INCOME: t("profile.billing.transaction.income"),
    OUTCOME: t("profile.billing.transaction.outcome"),
    SYSTEM: t("profile.billing.transaction.system"),
  };

  return (
    <div className="overflow-hidden border border-white/10 bg-[#050505]">
      {/* Header */}
      <div className="flex items-center justify-between border-white/10 border-b bg-[#0a0a0a] p-4">
        <div className="flex items-center gap-2">
          <History className="text-pandora-cyan" size={14} />
          <div className="font-bold font-mono text-[10px] text-white/90 uppercase tracking-widest">
            {t("profile.billing.title")}
          </div>
        </div>
        <div className="font-mono text-[9px] text-gray-500 uppercase">
          {localizedLogs.length} LOGS DETECTED
        </div>
      </div>

      <div className="p-0 font-mono text-xs">
        {localizedLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-gray-600">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-white/5">
              <History className="opacity-20" size={20} />
            </div>
            <span className="font-bold text-[9px] uppercase tracking-[0.2em]">
              {t("profile.billing.noTransactions")}
            </span>
          </div>
        ) : (
          <div className="divide-y divide-white/5">
            {/* Desktop Header Row (Hidden on Mobile) */}
            <div className="hidden grid-cols-12 gap-4 border-white/5 border-b bg-white/[0.02] px-6 py-3 font-bold text-[9px] text-gray-500 uppercase tracking-wider sm:grid">
              <div className="col-span-2 flex items-center gap-2">ID | Type</div>
              <div className="col-span-5">Source / Activity</div>
              <div className="col-span-3 text-right">Amount</div>
              <div className="col-span-2 text-right">Timestamp</div>
            </div>

            {localizedLogs.map((log) => (
              <div
                className="group relative overflow-hidden px-4 py-4 transition-all duration-200 hover:bg-white/[0.03] sm:px-6 sm:py-3"
                key={log.id}
              >
                {/* Visual indicator bar */}
                <div
                  className={`absolute top-0 bottom-0 left-0 w-[2px] transition-all duration-300 ${
                    log.isIncome
                      ? "bg-green-500/0 group-hover:bg-green-500/50"
                      : "bg-pandora-cyan/0 group-hover:bg-pandora-cyan/50"
                  }`}
                />

                {/* Desktop View */}
                <div className="hidden grid-cols-12 items-center gap-4 sm:grid">
                  {/* ID & Type */}
                  <div className="col-span-2 flex items-center gap-3">
                    <div
                      className={`rounded-sm p-2 ${
                        log.isIncome ? "bg-green-500/10 text-green-500" : "bg-white/5 text-gray-400"
                      }`}
                    >
                      {log.isIncome ? <ArrowUpRight size={14} /> : <ArrowDownLeft size={14} />}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-[9px] text-gray-600 uppercase leading-none tracking-tighter">
                        #{log.id}
                      </span>
                      <span
                        className={`font-bold text-[10px] ${
                          log.isIncome ? "text-green-500/80" : "text-pandora-cyan/80"
                        }`}
                      >
                        {typeLabels[log.type] || log.type}
                      </span>
                    </div>
                  </div>

                  {/* Source */}
                  <div className="col-span-5 flex flex-col">
                    <span className="truncate font-bold text-sm text-white tracking-tight transition-colors group-hover:text-pandora-cyan">
                      {log.localizedSource}
                    </span>
                    <span className="truncate text-[10px] text-gray-500 uppercase tracking-widest opacity-50">
                      {log.details ||
                        (log.referenceId ? `#${log.referenceId.substring(0, 8)}` : "")}
                    </span>
                  </div>

                  {/* Amount */}
                  <div className="col-span-3 flex flex-col items-end text-right">
                    <span
                      className={`font-bold text-base ${
                        log.isIncome ? "text-green-400" : "text-white"
                      }`}
                    >
                      {log.formattedAmount}
                    </span>
                  </div>

                  {/* Date */}
                  <div className="col-span-2 flex flex-col items-end justify-center text-right">
                    <div className="flex items-center gap-1.5 text-gray-500 transition-colors group-hover:text-gray-400">
                      <Clock size={10} />
                      <span className="text-[10px]">{log.date}</span>
                    </div>
                  </div>
                </div>

                {/* Mobile View */}
                <div className="flex flex-col gap-3 sm:hidden">
                  <div className="flex items-start justify-between">
                    <div className="flex gap-3">
                      <div
                        className={`shrink-0 rounded-sm p-2.5 ${
                          log.isIncome
                            ? "bg-green-500/10 text-green-500"
                            : "bg-white/5 text-gray-400"
                        }`}
                      >
                        {log.isIncome ? <ArrowUpRight size={16} /> : <ArrowDownLeft size={16} />}
                      </div>
                      <div className="flex min-w-0 flex-col">
                        <span className="truncate pr-2 font-bold text-sm text-white">
                          {log.localizedSource}
                        </span>
                        <div className="mt-0.5 flex items-center gap-2">
                          <span className="font-mono text-[9px] text-gray-600">#{log.id}</span>
                          <span
                            className={`rounded-sm border px-1.5 py-0.5 font-bold text-[8px] tracking-wider ${getLogBadgeClasses(log.isIncome, log.type)}`}
                          >
                            {typeLabels[log.type] || log.type}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div
                      className={`shrink-0 font-bold text-base ${
                        log.isIncome ? "text-green-400" : "text-white"
                      }`}
                    >
                      {log.formattedAmount}
                    </div>
                  </div>
                  <div className="mt-1 flex items-center justify-between border-white/5 border-t pt-2">
                    <div className="flex max-w-[60%] items-center gap-1.5 truncate font-bold text-[9px] text-gray-500 uppercase tracking-widest opacity-50">
                      {log.details ||
                        (log.referenceId ? `#${log.referenceId.substring(0, 8)}` : "Completed")}
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] text-gray-500">
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
