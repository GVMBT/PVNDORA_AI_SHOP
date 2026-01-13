/**
 * AdminAccounting Component
 *
 * Полная панель P&L и бухгалтерии.
 * Локализация: RU
 */

import React, { memo, useState } from "react";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Percent,
  CreditCard,
  Users,
  Star,
  Shield,
  PiggyBank,
  BarChart3,
  RefreshCw,
  Plus,
  ArrowDownRight,
  Calculator,
  Coins,
} from "lucide-react";

// Revenue breakdown by currency (REAL amounts, no conversion)
export interface CurrencyRevenue {
  orders_count: number;
  revenue: number; // Real amount in this currency
  revenue_gross: number; // Before discounts
  discounts_given: number;
}

// Liabilities by currency
export interface CurrencyLiabilities {
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
  // REVENUE BY CURRENCY (Real amounts, no conversion!)
  // =====================================================================
  revenueByCurrency: Record<string, CurrencyRevenue>;

  // Legacy totals in USD (for backward compatibility)
  totalRevenue: number;
  revenueGross: number;
  totalDiscountsGiven: number;

  // =====================================================================
  // EXPENSES (Always in USD - suppliers are paid in $)
  // =====================================================================
  totalCogs: number;
  totalAcquiringFees: number;
  totalReferralPayouts: number;
  totalReserves: number;
  totalReviewCashbacks: number;
  totalReplacementCosts: number;
  totalOtherExpenses: number;

  // Insurance revenue (USD)
  totalInsuranceRevenue: number;

  // =====================================================================
  // LIABILITIES BY CURRENCY (Real amounts!)
  // =====================================================================
  liabilitiesByCurrency: Record<string, CurrencyLiabilities>;

  // Legacy liabilities
  totalUserBalances: number;
  pendingWithdrawals: number;

  // =====================================================================
  // PROFIT (In USD, since COGS is in $)
  // =====================================================================
  netProfit: number;
  grossProfit?: number;
  operatingProfit?: number;
  grossMarginPct?: number;
  netMarginPct?: number;

  // Reserves (USD)
  reservesAccumulated?: number;
  reservesUsed?: number;
  reservesAvailable?: number;

  // DEPRECATED: Old currency breakdown (kept for compatibility)
  currencyBreakdown?: Record<
    string,
    { orders_count: number; revenue_usd: number; revenue_fiat: number }
  >;
}

// Type aliases for union types
type AccountingPeriod = "today" | "month" | "all" | "custom";
type DisplayCurrency = "USD" | "RUB";

interface AdminAccountingProps {
  data?: AccountingData;
  onRefresh?: (
    period?: AccountingPeriod,
    customFrom?: string,
    customTo?: string,
    displayCurrency?: DisplayCurrency
  ) => void;
  onAddExpense?: () => void;
  isLoading?: boolean;
}

const formatMoney = (amount: number, currency: "USD" | "RUB" = "USD"): string => {
  const symbol = currency === "USD" ? "$" : "₽";
  const formatted = new Intl.NumberFormat("ru-RU", {
    minimumFractionDigits: currency === "RUB" ? 0 : 2,
    maximumFractionDigits: currency === "RUB" ? 0 : 2,
  }).format(amount);

  if (Math.abs(amount) >= 1000000) {
    return `${symbol}${(amount / 1000000).toFixed(2)}M`;
  } else if (Math.abs(amount) >= 1000) {
    return `${symbol}${(amount / 1000).toFixed(2)}K`;
  }
  return `${symbol}${formatted}`;
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
  displayCurrency: "USD" | "RUB";
  dualCurrency?: { usd: number; rub: number };
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

// Helper: render dual currency values
const renderDualCurrencyValue = (
  dualCurrency: { usd: number; rub: number },
  isExpense: boolean,
  valueColor: string,
  bold: boolean
) => (
  <>
    <span className={`font-mono ${valueColor} ${bold ? "font-bold text-lg" : ""}`}>
      {isExpense && dualCurrency.usd > 0 ? "-" : ""}
      {formatMoney(Math.abs(dualCurrency.usd), "USD")}
    </span>
    <span className={`font-mono text-xs ${valueColor} opacity-75`}>
      {isExpense && dualCurrency.rub > 0 ? "-" : ""}
      {formatMoney(Math.abs(dualCurrency.rub), "RUB")}
    </span>
  </>
);

// Helper: render single currency value
const renderSingleCurrencyValue = (
  value: number,
  isExpense: boolean,
  valueColor: string,
  bold: boolean,
  displayCurrency: "USD" | "RUB"
) => (
  <span className={`font-mono ${valueColor} ${bold ? "font-bold text-lg" : ""}`}>
    {isExpense && value > 0 ? "-" : ""}
    {formatMoney(Math.abs(value), displayCurrency)}
  </span>
);

const MetricRow: React.FC<MetricRowProps> = ({
  label,
  value,
  isExpense = false,
  isProfit = false,
  icon,
  indent = false,
  bold = false,
  displayCurrency,
  dualCurrency,
  tooltip,
}) => {
  const valueColor = getValueColor(isProfit, isExpense, value);
  const showDual = dualCurrency && (dualCurrency.usd > 0 || dualCurrency.rub > 0);

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
          {showDual && dualCurrency
            ? renderDualCurrencyValue(dualCurrency, isExpense, valueColor, bold)
            : renderSingleCurrencyValue(value, isExpense, valueColor, bold, displayCurrency)}
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
      // Refresh with new period (currency param kept for backward compatibility)
      if (onRefresh) onRefresh(p, undefined, undefined, "USD");
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

  // Get revenue breakdown - prioritize the explicitly typed new field
  // If fallback to currencyBreakdown happens, we must be careful with types
  const rawRevenue = d.revenueByCurrency || d.currencyBreakdown || {};
  const liabilitiesByCurrency = d.liabilitiesByCurrency || {};

  // Calculated metrics (in USD since COGS is in USD)
  // grossProfit and operatingExpenses are available via d.* properties
  const netMargin =
    d.netMarginPct ?? (d.totalRevenue > 0 ? (d.netProfit / d.totalRevenue) * 100 : 0);
  const avgOrderValue = d.totalOrders > 0 ? d.totalRevenue / d.totalOrders : 0;

  // Reserve calculation
  const reservesAccumulated = d.reservesAccumulated ?? d.totalReserves;
  const reservesUsed = d.reservesUsed ?? d.totalOtherExpenses;
  const reservesAvailable = d.reservesAvailable ?? reservesAccumulated - reservesUsed;

  // Format currency symbol
  const getCurrencySymbol = (currency: string) => {
    const symbols: Record<string, string> = {
      USD: "$",
      RUB: "₽",
      EUR: "€",
      UAH: "₴",
      TRY: "₺",
      INR: "₹",
    };
    return symbols[currency] || currency;
  };

  // Format money for specific currency
  const formatCurrencyAmount = (amount: number, currency: string): string => {
    const isInteger = ["RUB", "UAH", "TRY", "INR", "JPY", "KRW"].includes(currency);
    const formatted = new Intl.NumberFormat("ru-RU", {
      minimumFractionDigits: isInteger ? 0 : 2,
      maximumFractionDigits: isInteger ? 0 : 2,
    }).format(amount);
    return `${formatted} ${getCurrencySymbol(currency)}`;
  };

  // Helper to extract specific currency data safely with type assertion
  const getCurrencyData = (code: string): CurrencyRevenue => {
    const data = rawRevenue[code] as any;
    if (!data) {
      return { revenue: 0, revenue_gross: 0, discounts_given: 0, orders_count: 0 };
    }
    // Safe cast - assuming backend sends valid structure or we accept 0/undefined as missing
    return {
      revenue: data.revenue || data.revenue_fiat || 0,
      revenue_gross: data.revenue_gross || 0,
      discounts_given: data.discounts_given || 0,
      orders_count: data.orders_count || 0,
    };
  };

  const rubData = getCurrencyData("RUB");
  const usdData = getCurrencyData("USD");

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
                key={p}
                onClick={() => handlePeriodChange(p)}
                className={`px-3 py-1.5 text-xs font-mono uppercase transition-colors ${
                  period === p ? "bg-pandora-cyan text-black" : "text-gray-400 hover:text-white"
                }`}
              >
                {(() => {
                  const labels: Record<string, string> = { today: "Сегодня", month: "Месяц", all: "Всё" };
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
                onClick={() => {
                  if (onRefresh) onRefresh("custom", customFrom, customTo, "USD");
                }}
                className="text-xs text-pandora-cyan hover:underline"
              >
                ОК
              </button>
            </div>
          )}
          {onAddExpense && (
            <button
              onClick={onAddExpense}
              className="p-2 bg-[#0e0e0e] border border-white/10 rounded-sm hover:border-green-500 transition-colors flex items-center gap-1"
            >
              <Plus size={14} className="text-green-400" />
              <span className="text-xs text-green-400 hidden md:inline">Расход</span>
            </button>
          )}
          {onRefresh && (
            <button
              onClick={() =>
                onRefresh(period, customFrom || undefined, customTo || undefined, "USD")
              }
              disabled={isLoading}
              className="p-2 bg-[#0e0e0e] border border-white/10 rounded-sm hover:border-pandora-cyan transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={`text-gray-400 ${isLoading ? "animate-spin" : ""}`} />
            </button>
          )}
        </div>
      </div>

      {/* =====================================================================
          НОВЫЙ БЛОК: РАЗДЕЛЬНЫЕ ПОТОКИ (RUB vs USD)
          ===================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ЛЕВАЯ КОЛОНКА: РУБЛЕВАЯ ЗОНА 🇷🇺 */}
        <div className="bg-[#0e0e0e] border border-white/10 p-5 rounded-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Coins size={100} className="text-blue-400" />
          </div>

          <div className="flex items-center gap-2 mb-6 relative z-10">
            <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-bold">
              ₽
            </div>
            <div>
              <h4 className="font-bold text-white text-lg">Рублевый поток</h4>
              <p className="text-xs text-gray-500">Платежи из РФ (СБП, Карты)</p>
            </div>
          </div>

          <div className="space-y-4 relative z-10">
            {/* Валовая в рублях */}
            <div className="flex justify-between items-end border-b border-white/5 pb-2">
              <span className="text-gray-400 text-sm">Валовая выручка</span>
              <div className="text-right">
                <div className="text-xl font-mono text-white font-bold">
                  {formatMoney(rubData.revenue_gross || 0, "RUB")}
                </div>
                <div className="text-xs text-gray-500">Цена товаров до скидок</div>
              </div>
            </div>

            {/* Скидки в рублях */}
            <div className="flex justify-between items-end border-b border-white/5 pb-2">
              <span className="text-gray-400 text-sm flex items-center gap-1">
                <Percent size={12} /> Скидки (промокоды)
              </span>
              <div className="text-right">
                <div className="text-lg font-mono text-red-400">
                  -{formatMoney(rubData.discounts_given || 0, "RUB")}
                </div>
              </div>
            </div>

            {/* Чистая в рублях */}
            <div className="flex justify-between items-end pt-2">
              <span className="text-blue-400 font-bold text-sm">Чистая выручка (RUB)</span>
              <div className="text-right">
                <div className="text-2xl font-mono text-blue-400 font-bold">
                  {formatMoney(rubData.revenue || 0, "RUB")}
                </div>
                <div className="text-xs text-gray-500">{rubData.orders_count || 0} заказов</div>
              </div>
            </div>
          </div>
        </div>

        {/* ПРАВАЯ КОЛОНКА: ДОЛЛАРОВАЯ ЗОНА 🇺🇸 */}
        <div className="bg-[#0e0e0e] border border-white/10 p-5 rounded-sm relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <DollarSign size={100} className="text-green-400" />
          </div>

          <div className="flex items-center gap-2 mb-6 relative z-10">
            <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center text-green-400 font-bold">
              $
            </div>
            <div>
              <h4 className="font-bold text-white text-lg">Валютный поток</h4>
              <p className="text-xs text-gray-500">Платежи из мира (Crypto, Stripe)</p>
            </div>
          </div>

          <div className="space-y-4 relative z-10">
            {/* Валовая в USD */}
            <div className="flex justify-between items-end border-b border-white/5 pb-2">
              <span className="text-gray-400 text-sm">Валовая выручка</span>
              <div className="text-right">
                <div className="text-xl font-mono text-white font-bold">
                  {formatMoney(usdData.revenue_gross || 0, "USD")}
                </div>
                <div className="text-xs text-gray-500">Цена товаров до скидок</div>
              </div>
            </div>

            {/* Скидки в USD */}
            <div className="flex justify-between items-end border-b border-white/5 pb-2">
              <span className="text-gray-400 text-sm flex items-center gap-1">
                <Percent size={12} /> Скидки (промокоды)
              </span>
              <div className="text-right">
                <div className="text-lg font-mono text-red-400">
                  -{formatMoney(usdData.discounts_given || 0, "USD")}
                </div>
              </div>
            </div>

            {/* Чистая в USD */}
            <div className="flex justify-between items-end pt-2">
              <span className="text-green-400 font-bold text-sm">Чистая выручка (USD)</span>
              <div className="text-right">
                <div className="text-2xl font-mono text-green-400 font-bold">
                  {formatMoney(usdData.revenue || 0, "USD")}
                </div>
                <div className="text-xs text-gray-500">{usdData.orders_count || 0} заказов</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* P&L Statement (РАСХОДЫ И ИТОГИ) */}
      <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-gray-500 font-mono mb-6 pb-2 border-b border-white/10 flex items-center gap-2">
          <Calculator size={14} />
          Сводный финансовый отчет (Консолидация в USD)
        </h4>

        {/* 1. Общая выручка (сконвертированная) */}
        <div className="mb-6 bg-[#151515] p-4 rounded-sm">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-400 text-sm uppercase">
              1. Общая Чистая Выручка (Total Net Revenue)
            </span>
            <span className="text-white font-mono font-bold text-xl">
              {formatMoney(d.totalRevenue, "USD")}
            </span>
          </div>
          <div className="text-xs text-gray-600 text-right">
            * Сумма рублевой и долларовой выручки (рубли конвертированы в USD по курсу на момент
            оплаты)
          </div>

          {d.totalInsuranceRevenue > 0 && (
            <div className="flex justify-between items-center mt-2 pt-2 border-t border-white/5 text-sm">
              <span className="text-gray-400 pl-4 flex items-center gap-2">
                <Shield size={12} /> + Доход от страховок
              </span>
              <span className="text-green-400 font-mono">
                {formatMoney(d.totalInsuranceRevenue, "USD")}
              </span>
            </div>
          )}
        </div>

        {/* 2. Расходы */}
        <div className="mb-6">
          <div className="text-xs uppercase text-red-400 font-mono mb-3 px-2">
            2. Глобальные расходы (USD)
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 px-4">
            {/* Себестоимость */}
            <div className="col-span-1 md:col-span-2 flex justify-between items-center border-b border-white/5 pb-2 mb-2">
              <span className="text-white font-bold text-sm">Себестоимость товаров (COGS)</span>
              <span className="text-red-400 font-mono font-bold">
                {formatMoney(d.totalCogs, "USD")}
              </span>
            </div>

            <MetricRow
              label="Эквайринг (комиссии)"
              value={d.totalAcquiringFees}
              isExpense
              displayCurrency="USD"
            />
            <MetricRow
              label="Реферальные выплаты"
              value={d.totalReferralPayouts}
              isExpense
              displayCurrency="USD"
            />
            <MetricRow
              label="Резервы (маркетинг 5%)"
              value={d.totalReserves}
              isExpense
              displayCurrency="USD"
            />
            <MetricRow
              label="Кэшбэк за отзывы"
              value={d.totalReviewCashbacks}
              isExpense
              displayCurrency="USD"
            />
            <MetricRow
              label="Замены по гарантии"
              value={d.totalReplacementCosts}
              isExpense
              displayCurrency="USD"
            />
            {d.totalOtherExpenses > 0 && (
              <MetricRow
                label="Прочие расходы"
                value={d.totalOtherExpenses}
                isExpense
                displayCurrency="USD"
              />
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
                (Рублевая выручка + Долларовая выручка) - Все расходы = Net Profit
              </p>
            </div>
            <div className="text-right">
              <div
                className={`text-4xl font-mono font-bold ${d.netProfit >= 0 ? "text-green-400" : "text-red-400"}`}
              >
                {formatMoney(d.netProfit, "USD")}
              </div>
              <div className="text-sm font-mono text-gray-400 mt-1">
                {formatPercent(netMargin)} маржинальность
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Резервы и Обязательства - оставляем старые блоки, они полезные, но сдвинем вниз */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Резервы (в USD) */}
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
                {formatMoney(reservesAvailable, "USD")}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-500">
                Всего отложено: {formatMoney(reservesAccumulated, "USD")}
              </div>
              <div className="text-xs text-gray-500">
                Потрачено: {formatMoney(reservesUsed, "USD")}
              </div>
            </div>
          </div>
        </div>

        {/* Обязательства */}
        <div className="bg-[#0e0e0e] border border-red-500/30 p-6 rounded-sm">
          <h4 className="text-xs uppercase text-red-400 font-mono mb-4 pb-2 border-b border-white/10">
            Обязательства перед юзерами
          </h4>

          <div className="space-y-2">
            {Object.entries(liabilitiesByCurrency).map(([curr, val]) => (
              <div key={curr} className="flex justify-between text-sm">
                <span className="text-gray-400">{curr}:</span>
                <span className="text-white font-mono">
                  {formatCurrencyAmount(
                    (val.user_balances || 0) + (val.pending_withdrawals || 0),
                    curr
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(AdminAccounting);
