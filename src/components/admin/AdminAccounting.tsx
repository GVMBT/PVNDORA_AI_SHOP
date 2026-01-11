/**
 * AdminAccounting Component
 * 
 * Полная панель P&L и бухгалтерии.
 * Локализация: RU
 */

import React, { memo, useState } from 'react';
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
  ArrowDownRight
} from 'lucide-react';

// Revenue breakdown by currency (REAL amounts, no conversion)
export interface CurrencyRevenue {
  orders_count: number;
  revenue: number;        // Real amount in this currency
  revenue_gross: number;  // Before discounts
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
  revenueByСurrency: Record<string, CurrencyRevenue>;
  
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
  currencyBreakdown?: Record<string, { orders_count: number; revenue_usd: number; revenue_fiat: number }>;
}

interface AdminAccountingProps {
  data?: AccountingData;
  onRefresh?: (period?: 'today' | 'month' | 'all' | 'custom', customFrom?: string, customTo?: string, displayCurrency?: 'USD' | 'RUB') => void;
  onAddExpense?: () => void;
  isLoading?: boolean;
}

const formatMoney = (amount: number, currency: 'USD' | 'RUB' = 'USD'): string => {
  const symbol = currency === 'USD' ? '$' : '₽';
  const formatted = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: currency === 'RUB' ? 0 : 2,
    maximumFractionDigits: currency === 'RUB' ? 0 : 2,
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
  displayCurrency: 'USD' | 'RUB';  // Add displayCurrency as prop
  dualCurrency?: { usd: number; rub: number };  // Optional dual currency display
  tooltip?: string;  // Optional tooltip
}

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
  tooltip
}) => {
  const valueColor = isProfit 
    ? (value >= 0 ? 'text-green-400' : 'text-red-400')
    : isExpense 
      ? 'text-red-400' 
      : 'text-white';
  
  // Show dual currency if provided
  const showDual = dualCurrency && (dualCurrency.usd > 0 || dualCurrency.rub > 0);
  
  return (
    <div className={`py-2 ${indent ? 'pl-6' : ''} ${bold ? 'border-t border-white/20 pt-3 mt-2' : ''}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-gray-400">
          {icon && <span className="text-gray-500">{icon}</span>}
          <span className={bold ? 'font-bold text-white' : ''}>{label}</span>
          {tooltip && (
            <span className="text-xs text-gray-500 cursor-help" title={tooltip}>ℹ️</span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1">
          {showDual ? (
            <>
              <span className={`font-mono ${valueColor} ${bold ? 'font-bold text-lg' : ''}`}>
                {isExpense && dualCurrency.usd > 0 ? '-' : ''}{formatMoney(Math.abs(dualCurrency.usd), 'USD')}
              </span>
              <span className={`font-mono text-xs ${valueColor} opacity-75`}>
                {isExpense && dualCurrency.rub > 0 ? '-' : ''}{formatMoney(Math.abs(dualCurrency.rub), 'RUB')}
              </span>
            </>
          ) : (
            <span className={`font-mono ${valueColor} ${bold ? 'font-bold text-lg' : ''}`}>
              {isExpense && value > 0 ? '-' : ''}{formatMoney(Math.abs(value), displayCurrency)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

const AdminAccounting: React.FC<AdminAccountingProps> = ({ 
  data,
  onRefresh,
  onAddExpense,
  isLoading = false
}) => {
  const [period, setPeriod] = useState<'today' | 'month' | 'all' | 'custom'>('all');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [showDatePicker, setShowDatePicker] = useState(false);
  
  // Handle period change and refresh
  const handlePeriodChange = (p: 'today' | 'month' | 'all' | 'custom') => {
    setPeriod(p);
    if (p === 'custom') {
      setShowDatePicker(true);
    } else {
      setShowDatePicker(false);
      // Refresh with new period (currency param kept for backward compatibility)
      if (onRefresh) onRefresh(p, undefined, undefined, 'USD');
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
    revenueByСurrency: {},
    liabilitiesByCurrency: {},
  };

  // Get revenue breakdown
  const revenueByСurrency = d.revenueByСurrency || d.currencyBreakdown || {};
  const liabilitiesByCurrency = d.liabilitiesByCurrency || {};
  
  // Calculated metrics (in USD since COGS is in USD)
  const grossProfit = d.grossProfit ?? (d.totalRevenue - d.totalCogs);
  const operatingExpenses = d.totalAcquiringFees + d.totalReferralPayouts + d.totalReserves + d.totalReviewCashbacks + d.totalReplacementCosts;
  const operatingProfit = d.operatingProfit ?? (grossProfit - operatingExpenses);
  const grossMargin = d.grossMarginPct ?? (d.totalRevenue > 0 ? (grossProfit / d.totalRevenue) * 100 : 0);
  const netMargin = d.netMarginPct ?? (d.totalRevenue > 0 ? (d.netProfit / d.totalRevenue) * 100 : 0);
  const avgOrderValue = d.totalOrders > 0 ? d.totalRevenue / d.totalOrders : 0;
  
  // Reserve calculation
  const reservesAccumulated = d.reservesAccumulated ?? d.totalReserves;
  const reservesUsed = d.reservesUsed ?? d.totalOtherExpenses;
  const reservesAvailable = d.reservesAvailable ?? (reservesAccumulated - reservesUsed);
  
  // Format currency symbol
  const getCurrencySymbol = (currency: string) => {
    const symbols: Record<string, string> = {
      USD: '$', RUB: '₽', EUR: '€', UAH: '₴', TRY: '₺', INR: '₹',
    };
    return symbols[currency] || currency;
  };
  
  // Format money for specific currency
  const formatCurrencyAmount = (amount: number, currency: string): string => {
    const isInteger = ['RUB', 'UAH', 'TRY', 'INR', 'JPY', 'KRW'].includes(currency);
    const formatted = new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: isInteger ? 0 : 2,
      maximumFractionDigits: isInteger ? 0 : 2,
    }).format(amount);
    return `${formatted} ${getCurrencySymbol(currency)}`;
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
            {(['today', 'month', 'all', 'custom'] as const).map((p) => (
              <button
                key={p}
                onClick={() => handlePeriodChange(p)}
                className={`px-3 py-1.5 text-xs font-mono uppercase transition-colors ${
                  period === p 
                    ? 'bg-pandora-cyan text-black' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {p === 'today' ? 'Сегодня' : p === 'month' ? 'Месяц' : p === 'all' ? 'Всё' : 'Период'}
              </button>
            ))}
          </div>
          
          {/* Custom Date Range */}
          {showDatePicker && period === 'custom' && (
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
                  if (onRefresh) onRefresh('custom', customFrom, customTo, 'USD');
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
              onClick={() => onRefresh(period, customFrom || undefined, customTo || undefined, 'USD')}
              disabled={isLoading}
              className="p-2 bg-[#0e0e0e] border border-white/10 rounded-sm hover:border-pandora-cyan transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={`text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* =====================================================================
          ВЫРУЧКА ПО ВАЛЮТАМ (макроуровень: только валовая выручка)
          ===================================================================== */}
      {Object.keys(revenueByСurrency).length > 0 && (
        <div className="bg-[#0e0e0e] border border-green-500/30 p-4 rounded-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 text-green-400 text-xs uppercase">
              <DollarSign size={14} />
              Выручка по валютам (валовая выручка)
            </div>
            <div className="text-xs text-gray-500">
              Чистая прибыль: <span className={`font-bold ${d.netProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                {formatMoney(d.netProfit, 'USD')}
              </span>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(revenueByСurrency).map(([currency, stats]) => {
              // Handle both old and new data format
              const revenueGross = 'revenue_gross' in stats ? stats.revenue_gross : (stats as any).revenue_fiat || 0;
              const ordersCount = stats.orders_count || 0;
              
              return (
                <div key={currency} className="bg-[#1a1a1a] border border-green-500/20 p-4 rounded-sm">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-lg font-bold text-white flex items-center gap-2">
                      {getCurrencySymbol(currency)}
                      <span className="text-xs text-gray-500 font-normal">{currency}</span>
                    </span>
                    <span className="text-xs text-gray-500 bg-[#0e0e0e] px-2 py-1 rounded">
                      {ordersCount} заказов
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center pt-1">
                      <span className="text-xs text-gray-400">Валовая выручка:</span>
                      <span className="text-white font-mono font-bold text-lg" title="Наша цена продуктов БЕЗ промокодов (реальные суммы оплат)">
                        {formatCurrencyAmount(revenueGross, currency)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-3 text-xs text-gray-500 flex items-center gap-1">
            💡 Показаны реальные суммы валовой выручки в каждой валюте, без конвертации. Чистая прибыль рассчитывается после всех расходов (USD).
          </div>
        </div>
      )}

      {/* Ключевые метрики (макроуровень: валовая выручка + чистая прибыль) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#0e0e0e] border border-green-500/30 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase mb-2">
            <DollarSign size={14} />
            Валовая выручка (все валюты)
          </div>
          <div className="text-2xl font-bold text-white font-mono">{formatMoney(d.revenueGross, 'USD')}</div>
          <div className="text-xs text-gray-500 mt-1">
            {Object.entries(revenueByСurrency).map(([curr, s]) => {
              const gross = 'revenue_gross' in s ? s.revenue_gross : 0;
              return `${formatCurrencyAmount(gross, curr)}`;
            }).join(' + ')} • {d.totalOrders} заказов
          </div>
          <div className="text-xs text-gray-600 mt-1">Наша цена продуктов БЕЗ промокодов</div>
        </div>
        
        <div className="bg-[#0e0e0e] border border-green-500/30 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase mb-2">
            <PiggyBank size={14} />
            Чистая прибыль (Net Profit)
          </div>
          <div className={`text-2xl font-bold font-mono ${d.netProfit >= 0 ? 'text-green-400' : 'text-red-400'}`} title="Чистая выручка минус ВСЕ расходы (COGS + операционные + прочие)">
            {formatMoney(d.netProfit, 'USD')}
          </div>
          <div className="text-xs text-gray-500 mt-1">{formatPercent(netMargin)} маржа</div>
          <div className="text-xs text-gray-600 mt-1">После всех расходов (USD)</div>
        </div>
      </div>

      {/* P&L Statement (выручка в $ и ₽, расходы в USD) */}
      <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-gray-500 font-mono mb-4 pb-2 border-b border-white/10">
          Отчёт о финансовых результатах
          <span className="text-gray-600 ml-2 normal-case">• выручка: реальные суммы $ и ₽ • расходы: в USD (платим поставщику в $)</span>
        </h4>
        
        {/* Выручка */}
        <div className="mb-4">
          <div className="text-xs uppercase text-pandora-cyan font-mono mb-2">
            Выручка (реальные суммы по валютам)
            <span className="text-gray-600 ml-2 normal-case text-xs">• показываем $ и ₽ где возможно</span>
          </div>
          
          {/* Валовая выручка - двойное значение $/RUB (только реальные суммы!) */}
          <MetricRow 
            label="Валовая выручка" 
            value={d.revenueGross} 
            icon={<DollarSign size={14} />}
            displayCurrency="USD"
            dualCurrency={{
              usd: revenueByСurrency['USD']?.revenue_gross || 0,
              rub: revenueByСurrency['RUB']?.revenue_gross || 0
            }}
            tooltip="Валовая выручка = сумма всех заказов по нашим ценам (products.price) БЕЗ применения промокодов. Это наша цена до скидок. Показаны реальные суммы в $ и ₽, без конвертации."
          />
          
          {/* Скидки - двойное значение $/RUB (только реальные суммы!) */}
          <MetricRow 
            label="Скидки (промокоды)" 
            value={d.totalDiscountsGiven} 
            isExpense 
            indent
            icon={<Percent size={14} />}
            displayCurrency="USD"
            dualCurrency={{
              usd: revenueByСurrency['USD']?.discounts_given || 0,
              rub: revenueByСurrency['RUB']?.discounts_given || 0
            }}
            tooltip="Скидки = сумма скидок через активированные промокоды. Например: пользователь покупает за 5000₽, активирует промокод 10%, мы фиксируем 500₽ как предоставленную скидку. Показаны реальные суммы в $ и ₽."
          />
          
          {/* Чистая выручка - двойное значение $/RUB (только реальные суммы!) */}
          <MetricRow 
            label="Чистая выручка (Net Revenue)" 
            value={d.totalRevenue} 
            bold
            displayCurrency="USD"
            dualCurrency={{
              usd: revenueByСurrency['USD']?.revenue || 0,
              rub: revenueByСurrency['RUB']?.revenue || 0
            }}
            tooltip="Чистая выручка (Net Revenue) = реальная сумма, которую заплатили пользователи (после применения промокодов). Это ДО расходов. НЕ путать с чистой прибылью (Net Profit) - чистая прибыль это ЧИСТАЯ ВЫРУЧКА минус ВСЕ расходы. Показаны реальные суммы в $ и ₽, без конвертации."
          />
          
          {d.totalInsuranceRevenue > 0 && (
            <MetricRow 
              label="Доход от страховок" 
              value={d.totalInsuranceRevenue} 
              indent
              icon={<Shield size={14} />}
              displayCurrency="USD"
              tooltip="Доход от продажи страховок на замену товара"
            />
          )}
        </div>

        {/* Себестоимость */}
        <div className="mb-4">
          <div className="text-xs uppercase text-pandora-cyan font-mono mb-2">Себестоимость (платим поставщику в $)</div>
          <MetricRow 
            label="Себестоимость товаров (COGS)" 
            value={d.totalCogs} 
            isExpense
            icon={<DollarSign size={14} />}
            displayCurrency="USD"
          />
          <MetricRow 
            label="Валовая прибыль" 
            value={grossProfit} 
            isProfit
            bold
            displayCurrency="USD"
          />
        </div>

        {/* Операционные расходы */}
        <div className="mb-4">
          <div className="text-xs uppercase text-pandora-cyan font-mono mb-2">Операционные расходы</div>
          <MetricRow 
            label="Эквайринг (СБП/карта/крипта)" 
            value={d.totalAcquiringFees} 
            isExpense
            indent
            icon={<CreditCard size={14} />}
            displayCurrency="USD"
          />
          <MetricRow 
            label="Реферальные выплаты (3 линии)" 
            value={d.totalReferralPayouts} 
            isExpense
            indent
            icon={<Users size={14} />}
            displayCurrency="USD"
          />
          <MetricRow 
            label="Кэшбэк за отзывы (5%)" 
            value={d.totalReviewCashbacks} 
            isExpense
            indent
            icon={<Star size={14} />}
            displayCurrency="USD"
          />
          <MetricRow 
            label="Страховые замены" 
            value={d.totalReplacementCosts} 
            isExpense
            indent
            icon={<Shield size={14} />}
            displayCurrency="USD"
          />
          <MetricRow 
            label="Резервы (маркетинг + непредв.)" 
            value={d.totalReserves} 
            isExpense
            indent
            icon={<PiggyBank size={14} />}
            displayCurrency="USD"
          />
          <MetricRow 
            label="Операционная прибыль" 
            value={operatingProfit} 
            isProfit
            bold
            displayCurrency="USD"
          />
        </div>

        {/* Прочие расходы */}
        {d.totalOtherExpenses > 0 && (
          <div className="mb-4">
            <div className="text-xs uppercase text-pandora-cyan font-mono mb-2">Прочие расходы</div>
            <MetricRow 
              label="Прямые расходы (из резервов)" 
              value={d.totalOtherExpenses} 
              isExpense
              indent
              icon={<ArrowDownRight size={14} />}
              displayCurrency="USD"
            />
          </div>
        )}

        {/* Чистая прибыль */}
        <div className="pt-4 border-t-2 border-pandora-cyan/30">
          <MetricRow 
            label="ЧИСТАЯ ПРИБЫЛЬ (Net Profit)" 
            value={d.netProfit} 
            isProfit
            bold
            displayCurrency="USD"
            tooltip="Чистая прибыль (Net Profit) = Чистая выручка минус ВСЕ расходы (COGS + операционные расходы + прочие расходы) плюс доходы от страховок. Это то, что реально остаётся после всех расходов и обязательств."
          />
        </div>
      </div>

      {/* Резервы (в USD) */}
      <div className="bg-[#0e0e0e] border border-yellow-500/30 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-yellow-400 font-mono mb-4 pb-2 border-b border-white/10 flex items-center gap-2">
          <PiggyBank size={14} />
          Резервы (8% от выручки, USD)
        </h4>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div className="text-xs text-gray-500 uppercase">Накоплено</div>
            <div className="text-lg font-mono text-yellow-400">{formatMoney(reservesAccumulated, 'USD')}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Использовано</div>
            <div className="text-lg font-mono text-red-400">{formatMoney(reservesUsed, 'USD')}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Доступно</div>
            <div className={`text-lg font-mono ${reservesAvailable >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatMoney(reservesAvailable, 'USD')}
            </div>
          </div>
        </div>
        <div className="text-xs text-gray-500">
          💡 Резервы = 5% маркетинг + 3% непредвиденные. При добавлении расхода с категорией "marketing" или "unforeseen" он списывается из резервов.
        </div>
      </div>

      {/* =====================================================================
          ОБЯЗАТЕЛЬСТВА ПО ВАЛЮТАМ (реальные суммы!)
          Примечание: Балансы пользователей УЖЕ включают реферальные выплаты.
          Реферальные выплаты идут в баланс, поэтому они согласованы с этой графой.
          ===================================================================== */}
      <div className="bg-[#0e0e0e] border border-red-500/30 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-red-400 font-mono mb-4 pb-2 border-b border-white/10">
          Обязательства (деньги пользователей по валютам)
          <span className="text-gray-600 ml-2 normal-case text-xs">• включают реферальные выплаты</span>
        </h4>
        
        {Object.keys(liabilitiesByCurrency).length > 0 ? (
          <div className="space-y-4">
            {/* По каждой валюте */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(liabilitiesByCurrency).map(([currency, data]) => (
                <div key={currency} className="bg-[#1a1a1a] border border-red-500/20 p-4 rounded-sm">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-lg font-bold text-white flex items-center gap-2">
                      {getCurrencySymbol(currency)}
                      <span className="text-xs text-gray-500 font-normal">{currency}</span>
                    </span>
                    <span className="text-xs text-gray-500 bg-[#0e0e0e] px-2 py-1 rounded">
                      {data.users_count || 0} польз.
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-400">Балансы:</span>
                      <span className="text-red-400 font-mono">
                        {formatCurrencyAmount(data.user_balances || 0, currency)}
                      </span>
                    </div>
                    {(data.pending_withdrawals || 0) > 0 && (
                      <div className="flex justify-between items-center">
                        <span className="text-xs text-gray-400">Ожидают вывода:</span>
                        <span className="text-orange-400 font-mono">
                          {formatCurrencyAmount(data.pending_withdrawals || 0, currency)}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between items-center pt-2 border-t border-white/10">
                      <span className="text-xs text-red-400 font-bold">Итого:</span>
                      <span className="text-red-400 font-mono font-bold">
                        {formatCurrencyAmount((data.user_balances || 0) + (data.pending_withdrawals || 0), currency)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="text-xs text-gray-500 flex items-center gap-1">
              💡 Показаны реальные суммы обязательств в каждой валюте
            </div>
          </div>
        ) : (
          // Fallback to old format
          <div>
            <MetricRow 
              label="Балансы пользователей" 
              value={d.totalUserBalances} 
              isExpense
              displayCurrency="USD"
            />
            <MetricRow 
              label="Ожидают вывода" 
              value={d.pendingWithdrawals} 
              isExpense
              displayCurrency="USD"
            />
            <MetricRow 
              label="Всего обязательств" 
              value={d.totalUserBalances + d.pendingWithdrawals} 
              isExpense
              bold
              displayCurrency="USD"
            />
          </div>
        )}
      </div>

      {/* Быстрая статистика (USD) */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div className="bg-[#0e0e0e] border border-white/10 p-3 rounded-sm">
          <div className="text-gray-500 uppercase">Средний чек (USD)</div>
          <div className="text-white font-mono mt-1">{formatMoney(avgOrderValue, 'USD')}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-3 rounded-sm">
          <div className="text-gray-500 uppercase">COGS на заказ</div>
          <div className="text-white font-mono mt-1">{formatMoney(d.totalOrders > 0 ? d.totalCogs / d.totalOrders : 0, 'USD')}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-3 rounded-sm">
          <div className="text-gray-500 uppercase">Эквайринг %</div>
          <div className="text-white font-mono mt-1">{formatPercent(d.totalRevenue > 0 ? (d.totalAcquiringFees / d.totalRevenue) * 100 : 0)}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-3 rounded-sm">
          <div className="text-gray-500 uppercase">Реферальные %</div>
          <div className="text-white font-mono mt-1">{formatPercent(d.totalRevenue > 0 ? (d.totalReferralPayouts / d.totalRevenue) * 100 : 0)}</div>
        </div>
      </div>
    </div>
  );
};

export default memo(AdminAccounting);
