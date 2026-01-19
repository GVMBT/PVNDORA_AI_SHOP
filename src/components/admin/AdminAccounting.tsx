/**
 * AdminAccounting Component
 *
 * Полная панель P&L и бухгалтерии.
 * Локализация: RU
 * Валюта: RUB only (после миграции)
 */

import {
  BarChart3,
  Calculator,
  Coins,
  Percent,
  PiggyBank,
  Plus,
  RefreshCw,
  Shield,
} from "lucide-react";
import type React from "react";
import { memo, useState } from "react";

// Revenue data (all in RUB)
export interface RevenueData {
  orders_count: number;
  revenue: number; // Net revenue in RUB
  revenue_gross: number; // Before discounts
  discounts_given: number;
}

// Liabilities (all in RUB)
export interface LiabilitiesData {
  user_balances: number;
  users_count: number;
  pending_withdrawals: number;
}

export interface AccountingData {
  // Filter info
  period?: string;
  startDate?: string;
  endDate?: string;

  // Orders
  totalOrders: number;
  ordersThisMonth?: number;
  ordersToday?: number;

  // =====================================================================
  // REVENUE (All in RUB after migration)
  // =====================================================================
  revenueByCurrency?: Record<string, RevenueData>;

  // Main totals (RUB)
  totalRevenue: number; // Net revenue
  revenueGross: number; // Before discounts
  totalDiscountsGiven: number;

  // =====================================================================
  // EXPENSES (All in RUB)
  // =====================================================================
  totalCogs: number;
  totalAcquiringFees: number;
  totalReferralPayouts: number;
  totalReserves: number;
  totalReviewCashbacks: number;
  totalReplacementCosts: number;
  totalOtherExpenses: number;

  // Insurance revenue (RUB)
  totalInsuranceRevenue: number;

  // =====================================================================
  // LIABILITIES (All in RUB)
  // =====================================================================
  liabilitiesByCurrency?: Record<string, LiabilitiesData>;

  // Legacy liabilities
  totalUserBalances: number;
  pendingWithdrawals: number;

  // =====================================================================
  // PROFIT (All in RUB)
  // =====================================================================
  netProfit: number;
  grossProfit?: number;
  operatingProfit?: number;
  grossMarginPct?: number;
  netMarginPct?: number;

  // Reserves (RUB)
  reservesAccumulated?: number;
  reservesUsed?: number;
  reservesAvailable?: number;
}

// Type aliases for union types
type AccountingPeriod = "today" | "month" | "all" | "custom";

interface AdminAccountingProps {
  data?: AccountingData;
  onRefresh?: (period?: AccountingPeriod, customFrom?: string, customTo?: string) => void;
  onAddExpense?: () => void;
  isLoading?: boolean;
}

const formatMoney = (amount: number): string => {
  const formatted = new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);

  if (Math.abs(amount) >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(2)}M ₽`;
  }
  if (Math.abs(amount) >= 1000) {
    return `${(amount / 1000).toFixed(1)}K ₽`;
  }
  return `${formatted} ₽`;
};

const formatPercent = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

interface MetricRowProps {
  label: string;
  value: number;
  isExpense?: boolean;
  isProfit?: boolean;
  icon?: React.ReactNode;
  indent?: boolean;
  bold?: boolean;
  tooltip?: string;
}

// Helper: determine value color based on expense/profit state
const getValueColor = (isProfit: boolean, isExpense: boolean, value: number): string => {
  if (isProfit) {
    return value >= 0 ? "text-green-400" : "text-red-400";
  }
  if (isExpense) {
    return "text-red-400";
  }
  return "text-white";
};

const MetricRow: React.FC<MetricRowProps> = ({
  label,
  value,
  isExpense = false,
  isProfit = false,
  icon,
  indent = false,
  bold = false,
  tooltip,
}) => {
  const valueColor = getValueColor(isProfit, isExpense, value);

  const containerClasses = `py-2 ${indent ? "pl-6" : ""} ${bold ? "border-t border-white/20 pt-3 mt-2" : ""}`;
  const labelClasses = bold ? "font-bold text-white" : "";

  return (
    <div className={containerClasses}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-gray-400">
          {icon && <span className="text-gray-500">{icon}</span>}
          <span className={labelClasses}>{label}</span>
          {tooltip && (
            <span className="cursor-help text-gray-500 text-xs" title={tooltip}>
              ℹ️
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          <span className={`font-mono ${valueColor} ${bold ? "font-bold text-lg" : ""}`}>
            {isExpense && value > 0 ? "-" : ""}
            {formatMoney(Math.abs(value))}
          </span>
        </div>
      </div>
    </div>
  );
};

const AdminAccounting: React.FC<AdminAccountingProps> = ({
  data,
  onRefresh,
  onAddExpense,
  isLoading = false,
}) => {
  const [period, setPeriod] = useState<"today" | "month" | "all" | "custom">("all");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [showDatePicker, setShowDatePicker] = useState(false);

  // Handle period change and refresh
  const handlePeriodChange = (p: "today" | "month" | "all" | "custom") => {
    setPeriod(p);
    if (p === "custom") {
      setShowDatePicker(true);
    } else {
      setShowDatePicker(false);
      if (onRefresh) {
        onRefresh(p, undefined, undefined);
      }
    }
  };

  const d = data || {
    totalRevenue: 0,
    revenueGross: 0,
    totalCogs: 0,
    totalAcquiringFees: 0,
    totalReferralPayouts: 0,
    totalReserves: 0,
    totalReviewCashbacks: 0,
    totalReplacementCosts: 0,
    totalOtherExpenses: 0,
    totalInsuranceRevenue: 0,
    totalDiscountsGiven: 0,
    totalUserBalances: 0,
    pendingWithdrawals: 0,
    netProfit: 0,
    totalOrders: 0,
    revenueByCurrency: {},
    liabilitiesByCurrency: {},
  };

  // Get revenue data (all in RUB now)
  const rubData = d.revenueByCurrency?.RUB || {
    revenue: d.totalRevenue,
    revenue_gross: d.revenueGross || d.totalRevenue,
    discounts_given: d.totalDiscountsGiven,
    orders_count: d.totalOrders,
  };

  // Calculated metrics (all in RUB)
  const netMargin =
    d.netMarginPct ?? (d.totalRevenue > 0 ? (d.netProfit / d.totalRevenue) * 100 : 0);

  // Reserve calculation
  const reservesAccumulated = d.reservesAccumulated ?? d.totalReserves;
  const reservesUsed = d.reservesUsed ?? d.totalOtherExpenses;
  const reservesAvailable = d.reservesAvailable ?? reservesAccumulated - reservesUsed;

  // Get liabilities (all in RUB)
  const liabilitiesRub = d.liabilitiesByCurrency?.RUB || {
    user_balances: d.totalUserBalances,
    pending_withdrawals: d.pendingWithdrawals,
    users_count: 0,
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h3 className="flex items-center gap-2 font-bold font-display text-lg text-white uppercase">
          <BarChart3 className="text-pandora-cyan" size={20} />
          Отчёт о прибылях и убытках
        </h3>
        <div className="flex items-center gap-2">
          {/* Селектор периода */}
          <div className="flex flex-wrap overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e]">
            {(["today", "month", "all", "custom"] as const).map((p) => (
              <button
                className={`px-3 py-1.5 font-mono text-xs uppercase transition-colors ${
                  period === p ? "bg-pandora-cyan text-black" : "text-gray-400 hover:text-white"
                }`}
                key={p}
                onClick={() => handlePeriodChange(p)}
                type="button"
              >
                {(() => {
                  const labels: Record<string, string> = {
                    today: "Сегодня",
                    month: "Месяц",
                    all: "Всё",
                  };
                  return labels[p] || "Период";
                })()}
              </button>
            ))}
          </div>

          {/* Custom Date Range */}
          {showDatePicker && period === "custom" && (
            <div className="flex items-center gap-2 rounded-sm border border-white/10 bg-[#0e0e0e] px-2 py-1">
              <input
                className="border-none bg-transparent text-white text-xs outline-none"
                onChange={(e) => setCustomFrom(e.target.value)}
                type="date"
                value={customFrom}
              />
              <span className="text-gray-500">—</span>
              <input
                className="border-none bg-transparent text-white text-xs outline-none"
                onChange={(e) => setCustomTo(e.target.value)}
                type="date"
                value={customTo}
              />
              <button
                className="text-pandora-cyan text-xs hover:underline"
                onClick={() => {
                  if (onRefresh) {
                    onRefresh("custom", customFrom, customTo);
                  }
                }}
                type="button"
              >
                ОК
              </button>
            </div>
          )}
          {onAddExpense && (
            <button
              className="flex items-center gap-1 rounded-sm border border-white/10 bg-[#0e0e0e] p-2 transition-colors hover:border-green-500"
              onClick={onAddExpense}
              type="button"
            >
              <Plus className="text-green-400" size={14} />
              <span className="hidden text-green-400 text-xs md:inline">Расход</span>
            </button>
          )}
          {onRefresh && (
            <button
              className="rounded-sm border border-white/10 bg-[#0e0e0e] p-2 transition-colors hover:border-pandora-cyan disabled:opacity-50"
              disabled={isLoading}
              onClick={() => onRefresh(period, customFrom || undefined, customTo || undefined)}
              type="button"
            >
              <RefreshCw className={`text-gray-400 ${isLoading ? "animate-spin" : ""}`} size={14} />
            </button>
          )}
        </div>
      </div>

      {/* БЛОК ВЫРУЧКИ (RUB) */}
      <div className="relative overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e] p-5">
        <div className="absolute top-0 right-0 p-4 opacity-10">
          <Coins className="text-blue-400" size={100} />
        </div>

        <div className="relative z-10 mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/20 font-bold text-blue-400">
            ₽
          </div>
          <div>
            <h4 className="font-bold text-lg text-white">Выручка</h4>
            <p className="text-gray-500 text-xs">Все платежи (СБП, Карты, CrystalPay)</p>
          </div>
        </div>

        <div className="relative z-10 space-y-4">
          {/* Валовая выручка */}
          <div className="flex items-end justify-between border-white/5 border-b pb-2">
            <span className="text-gray-400 text-sm">Валовая выручка</span>
            <div className="text-right">
              <div className="font-bold font-mono text-white text-xl">
                {formatMoney(rubData.revenue_gross || 0)}
              </div>
              <div className="text-gray-500 text-xs">Цена товаров до скидок</div>
            </div>
          </div>

          {/* Скидки */}
          <div className="flex items-end justify-between border-white/5 border-b pb-2">
            <span className="flex items-center gap-1 text-gray-400 text-sm">
              <Percent size={12} /> Скидки (промокоды)
            </span>
            <div className="text-right">
              <div className="font-mono text-lg text-red-400">
                -{formatMoney(rubData.discounts_given || 0)}
              </div>
            </div>
          </div>

          {/* Чистая выручка */}
          <div className="flex items-end justify-between pt-2">
            <span className="font-bold text-blue-400 text-sm">Чистая выручка</span>
            <div className="text-right">
              <div className="font-bold font-mono text-2xl text-blue-400">
                {formatMoney(rubData.revenue || 0)}
              </div>
              <div className="text-gray-500 text-xs">{rubData.orders_count || 0} заказов</div>
            </div>
          </div>
        </div>
      </div>

      {/* P&L Statement (РАСХОДЫ И ИТОГИ) */}
      <div className="rounded-sm border border-white/10 bg-[#0e0e0e] p-6">
        <h4 className="mb-6 flex items-center gap-2 border-white/10 border-b pb-2 font-mono text-gray-500 text-xs uppercase">
          <Calculator size={14} />
          Сводный финансовый отчет
        </h4>

        {/* 1. Общая выручка */}
        <div className="mb-6 rounded-sm bg-[#151515] p-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-gray-400 text-sm uppercase">1. Чистая Выручка (Net Revenue)</span>
            <span className="font-bold font-mono text-white text-xl">
              {formatMoney(d.totalRevenue)}
            </span>
          </div>

          {d.totalInsuranceRevenue > 0 && (
            <div className="mt-2 flex items-center justify-between border-white/5 border-t pt-2 text-sm">
              <span className="flex items-center gap-2 pl-4 text-gray-400">
                <Shield size={12} /> + Доход от страховок
              </span>
              <span className="font-mono text-green-400">
                {formatMoney(d.totalInsuranceRevenue)}
              </span>
            </div>
          )}
        </div>

        {/* 2. Расходы */}
        <div className="mb-6">
          <div className="mb-3 px-2 font-mono text-red-400 text-xs uppercase">2. Расходы</div>

          <div className="grid grid-cols-1 gap-x-8 gap-y-2 px-4 md:grid-cols-2">
            {/* Себестоимость */}
            <div className="col-span-1 mb-2 flex items-center justify-between border-white/5 border-b pb-2 md:col-span-2">
              <span className="font-bold text-sm text-white">Себестоимость товаров (COGS)</span>
              <span className="font-bold font-mono text-red-400">{formatMoney(d.totalCogs)}</span>
            </div>

            <MetricRow isExpense label="Эквайринг (комиссии)" value={d.totalAcquiringFees} />
            <MetricRow isExpense label="Реферальные выплаты" value={d.totalReferralPayouts} />
            <MetricRow isExpense label="Резервы (маркетинг 5%)" value={d.totalReserves} />
            <MetricRow isExpense label="Кэшбэк за отзывы" value={d.totalReviewCashbacks} />
            <MetricRow isExpense label="Замены по гарантии" value={d.totalReplacementCosts} />
            {d.totalOtherExpenses > 0 && (
              <MetricRow isExpense label="Прочие расходы" value={d.totalOtherExpenses} />
            )}
          </div>
        </div>

        {/* 3. ИТОГ */}
        <div className="mt-8 border-pandora-cyan border-l-4 bg-gradient-to-r from-pandora-cyan/5 to-transparent p-6">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="mb-1 font-bold font-display text-2xl text-white uppercase">
                Чистая Прибыль
              </h3>
              <p className="max-w-[300px] text-gray-500 text-xs">
                Выручка - Все расходы = Net Profit
              </p>
            </div>
            <div className="text-right">
              <div
                className={`font-bold font-mono text-4xl ${d.netProfit >= 0 ? "text-green-400" : "text-red-400"}`}
              >
                {formatMoney(d.netProfit)}
              </div>
              <div className="mt-1 font-mono text-gray-400 text-sm">
                {formatPercent(netMargin)} маржинальность
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Резервы и Обязательства */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Резервы */}
        <div className="rounded-sm border border-yellow-500/30 bg-[#0e0e0e] p-6">
          <h4 className="mb-4 flex items-center gap-2 border-white/10 border-b pb-2 font-mono text-xs text-yellow-400 uppercase">
            <PiggyBank size={14} />
            Фонд Резервов (Накоплено)
          </h4>
          <div className="flex items-end justify-between">
            <div>
              <div className="mb-1 text-gray-500 text-xs uppercase">Доступно сейчас</div>
              <div
                className={`font-mono text-2xl ${reservesAvailable >= 0 ? "text-white" : "text-red-400"}`}
              >
                {formatMoney(reservesAvailable)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-gray-500 text-xs">
                Всего отложено: {formatMoney(reservesAccumulated)}
              </div>
              <div className="text-gray-500 text-xs">Потрачено: {formatMoney(reservesUsed)}</div>
            </div>
          </div>
        </div>

        {/* Обязательства */}
        <div className="rounded-sm border border-red-500/30 bg-[#0e0e0e] p-6">
          <h4 className="mb-4 border-white/10 border-b pb-2 font-mono text-red-400 text-xs uppercase">
            Обязательства перед юзерами
          </h4>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Балансы пользователей:</span>
              <span className="font-mono text-white">
                {formatMoney(liabilitiesRub.user_balances || d.totalUserBalances)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Ожидают вывода:</span>
              <span className="font-mono text-white">
                {formatMoney(liabilitiesRub.pending_withdrawals || d.pendingWithdrawals)}
              </span>
            </div>
            <div className="flex justify-between border-white/10 border-t pt-2 text-sm">
              <span className="font-bold text-white">Итого:</span>
              <span className="font-bold font-mono text-red-400">
                {formatMoney(
                  (liabilitiesRub.user_balances || d.totalUserBalances) +
                    (liabilitiesRub.pending_withdrawals || d.pendingWithdrawals)
                )}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(AdminAccounting);
