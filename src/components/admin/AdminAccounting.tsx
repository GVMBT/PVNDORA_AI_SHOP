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

  if (Math.abs(amount) >= 1000000) {
    return `${(amount / 1000000).toFixed(2)}M ₽`;
  } else if (Math.abs(amount) >= 1000) {
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
            <span className="text-xs text-gray-500 cursor-help" title={tooltip}>
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
      if (onRefresh) onRefresh(p, undefined, undefined);
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
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h3 className="font-display font-bold text-white uppercase text-lg flex items-center gap-2">
          <BarChart3 size={20} className="text-pandora-cyan" />
          Отчёт о прибылях и убытках
        </h3>
        <div className="flex items-center gap-2">
          {/* Селектор периода */}
          <div className="flex flex-wrap bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
            {(["today", "month", "all", "custom"] as const).map((p) => (
              <button
                type="button"
                key={p}
                onClick={() => handlePeriodChange(p)}
                className={`px-3 py-1.5 text-xs font-mono uppercase transition-colors ${
                  period === p ? "bg-pandora-cyan text-black" : "text-gray-400 hover:text-white"
                }`}
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
            <div className="flex items-center gap-2 bg-[#0e0e0e] border border-white/10 px-2 py-1 rounded-sm">
              <input
                type="date"
                value={customFrom}
                onChange={(e) => setCustomFrom(e.target.value)}
                className="bg-transparent text-xs text-white border-none outline-none"
              />
              <span className="text-gray-500">—</span>
              <input
                type="date"
                value={customTo}
                onChange={(e) => setCustomTo(e.target.value)}
                className="bg-transparent text-xs text-white border-none outline-none"
              />
              <button
                type="button"
                onClick={() => {
                  if (onRefresh) onRefresh("custom", customFrom, customTo);
                }}
                className="text-xs text-pandora-cyan hover:underline"
              >
                ОК
              </button>
            </div>
          )}
          {onAddExpense && (
            <button
              type="button"
              onClick={onAddExpense}
              className="p-2 bg-[#0e0e0e] border border-white/10 rounded-sm hover:border-green-500 transition-colors flex items-center gap-1"
            >
              <Plus size={14} className="text-green-400" />
              <span className="text-xs text-green-400 hidden md:inline">Расход</span>
            </button>
          )}
          {onRefresh && (
            <button
              type="button"
              onClick={() => onRefresh(period, customFrom || undefined, customTo || undefined)}
              disabled={isLoading}
              className="p-2 bg-[#0e0e0e] border border-white/10 rounded-sm hover:border-pandora-cyan transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={`text-gray-400 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          )}
        </div>
      </div>

      {/* БЛОК ВЫРУЧКИ (RUB) */}
      <div className="bg-[#0e0e0e] border border-white/10 p-5 rounded-sm relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-10">
          <Coins size={100} className="text-blue-400" />
        </div>

        <div className="flex items-center gap-2 mb-6 relative z-10">
          <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold">
            ₽
          </div>
          <div>
            <h4 className="font-bold text-white text-lg">Выручка</h4>
            <p className="text-xs text-gray-500">Все платежи (СБП, Карты, CrystalPay)</p>
          </div>
        </div>

        <div className="space-y-4 relative z-10">
          {/* Валовая выручка */}
          <div className="flex justify-between items-end border-b border-white/5 pb-2">
            <span className="text-gray-400 text-sm">Валовая выручка</span>
            <div className="text-right">
              <div className="text-xl font-mono text-white font-bold">
                {formatMoney(rubData.revenue_gross || 0)}
              </div>
              <div className="text-xs text-gray-500">Цена товаров до скидок</div>
            </div>
          </div>

          {/* Скидки */}
          <div className="flex justify-between items-end border-b border-white/5 pb-2">
            <span className="text-gray-400 text-sm flex items-center gap-1">
              <Percent size={12} /> Скидки (промокоды)
            </span>
            <div className="text-right">
              <div className="text-lg font-mono text-red-400">
                -{formatMoney(rubData.discounts_given || 0)}
              </div>
            </div>
          </div>

          {/* Чистая выручка */}
          <div className="flex justify-between items-end pt-2">
            <span className="text-blue-400 font-bold text-sm">Чистая выручка</span>
            <div className="text-right">
              <div className="text-2xl font-mono text-blue-400 font-bold">
                {formatMoney(rubData.revenue || 0)}
              </div>
              <div className="text-xs text-gray-500">{rubData.orders_count || 0} заказов</div>
            </div>
          </div>
        </div>
      </div>

      {/* P&L Statement (РАСХОДЫ И ИТОГИ) */}
      <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-gray-500 font-mono mb-6 pb-2 border-b border-white/10 flex items-center gap-2">
          <Calculator size={14} />
          Сводный финансовый отчет
        </h4>

        {/* 1. Общая выручка */}
        <div className="mb-6 bg-[#151515] p-4 rounded-sm">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400 text-sm uppercase">1. Чистая Выручка (Net Revenue)</span>
            <span className="text-white font-mono font-bold text-xl">
              {formatMoney(d.totalRevenue)}
            </span>
          </div>

          {d.totalInsuranceRevenue > 0 && (
            <div className="flex justify-between items-center mt-2 pt-2 border-t border-white/5 text-sm">
              <span className="text-gray-400 pl-4 flex items-center gap-2">
                <Shield size={12} /> + Доход от страховок
              </span>
              <span className="text-green-400 font-mono">
                {formatMoney(d.totalInsuranceRevenue)}
              </span>
            </div>
          )}
        </div>

        {/* 2. Расходы */}
        <div className="mb-6">
          <div className="text-xs uppercase text-red-400 font-mono mb-3 px-2">2. Расходы</div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 px-4">
            {/* Себестоимость */}
            <div className="col-span-1 md:col-span-2 flex justify-between items-center border-b border-white/5 pb-2 mb-2">
              <span className="text-white font-bold text-sm">Себестоимость товаров (COGS)</span>
              <span className="text-red-400 font-mono font-bold">{formatMoney(d.totalCogs)}</span>
            </div>

            <MetricRow label="Эквайринг (комиссии)" value={d.totalAcquiringFees} isExpense />
            <MetricRow label="Реферальные выплаты" value={d.totalReferralPayouts} isExpense />
            <MetricRow label="Резервы (маркетинг 5%)" value={d.totalReserves} isExpense />
            <MetricRow label="Кэшбэк за отзывы" value={d.totalReviewCashbacks} isExpense />
            <MetricRow label="Замены по гарантии" value={d.totalReplacementCosts} isExpense />
            {d.totalOtherExpenses > 0 && (
              <MetricRow label="Прочие расходы" value={d.totalOtherExpenses} isExpense />
            )}
          </div>
        </div>

        {/* 3. ИТОГ */}
        <div className="bg-gradient-to-r from-pandora-cyan/5 to-transparent border-l-4 border-pandora-cyan p-6 mt-8">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-2xl font-bold text-white uppercase font-display mb-1">
                Чистая Прибыль
              </h3>
              <p className="text-xs text-gray-500 max-w-[300px]">
                Выручка - Все расходы = Net Profit
              </p>
            </div>
            <div className="text-right">
              <div
                className={`text-4xl font-mono font-bold ${d.netProfit >= 0 ? "text-green-400" : "text-red-400"}`}
              >
                {formatMoney(d.netProfit)}
              </div>
              <div className="text-sm font-mono text-gray-400 mt-1">
                {formatPercent(netMargin)} маржинальность
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Резервы и Обязательства */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Резервы */}
        <div className="bg-[#0e0e0e] border border-yellow-500/30 p-6 rounded-sm">
          <h4 className="text-xs uppercase text-yellow-400 font-mono mb-4 pb-2 border-b border-white/10 flex items-center gap-2">
            <PiggyBank size={14} />
            Фонд Резервов (Накоплено)
          </h4>
          <div className="flex justify-between items-end">
            <div>
              <div className="text-xs text-gray-500 uppercase mb-1">Доступно сейчас</div>
              <div
                className={`text-2xl font-mono ${reservesAvailable >= 0 ? "text-white" : "text-red-400"}`}
              >
                {formatMoney(reservesAvailable)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-500">
                Всего отложено: {formatMoney(reservesAccumulated)}
              </div>
              <div className="text-xs text-gray-500">Потрачено: {formatMoney(reservesUsed)}</div>
            </div>
          </div>
        </div>

        {/* Обязательства */}
        <div className="bg-[#0e0e0e] border border-red-500/30 p-6 rounded-sm">
          <h4 className="text-xs uppercase text-red-400 font-mono mb-4 pb-2 border-b border-white/10">
            Обязательства перед юзерами
          </h4>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Балансы пользователей:</span>
              <span className="text-white font-mono">
                {formatMoney(liabilitiesRub.user_balances || d.totalUserBalances)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Ожидают вывода:</span>
              <span className="text-white font-mono">
                {formatMoney(liabilitiesRub.pending_withdrawals || d.pendingWithdrawals)}
              </span>
            </div>
            <div className="flex justify-between text-sm pt-2 border-t border-white/10">
              <span className="text-white font-bold">Итого:</span>
              <span className="text-red-400 font-mono font-bold">
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
