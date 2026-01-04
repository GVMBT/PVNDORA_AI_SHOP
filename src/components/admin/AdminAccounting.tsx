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

export interface AccountingData {
  // Revenue
  totalRevenue: number;
  revenueGross: number;
  revenueThisMonth: number;
  revenueToday: number;
  
  // Costs
  totalCogs: number;
  totalAcquiringFees: number;
  totalReferralPayouts: number;
  totalReserves: number;
  totalReviewCashbacks: number;
  totalReplacementCosts: number;
  totalOtherExpenses: number;
  
  // Insurance
  totalInsuranceRevenue: number;
  
  // Discounts
  totalDiscountsGiven: number;
  
  // Liabilities
  totalUserBalances: number;
  pendingWithdrawals: number;
  
  // Calculated
  netProfit: number;
  
  // Orders
  totalOrders: number;
  ordersThisMonth: number;
  ordersToday: number;
  
  // Reserve usage (optional)
  reservesUsed?: number;
  reservesAvailable?: number;
}

interface AdminAccountingProps {
  data?: AccountingData;
  onRefresh?: () => void;
  onAddExpense?: () => void;
  isLoading?: boolean;
}

const formatMoney = (amount: number): string => {
  if (Math.abs(amount) >= 1000000) {
    return `$${(amount / 1000000).toFixed(2)}M`;
  } else if (Math.abs(amount) >= 1000) {
    return `$${(amount / 1000).toFixed(2)}K`;
  }
  return `$${amount.toFixed(2)}`;
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
}

const MetricRow: React.FC<MetricRowProps> = ({ 
  label, 
  value, 
  isExpense = false, 
  isProfit = false,
  icon,
  indent = false,
  bold = false
}) => {
  const valueColor = isProfit 
    ? (value >= 0 ? 'text-green-400' : 'text-red-400')
    : isExpense 
      ? 'text-red-400' 
      : 'text-white';
  
  return (
    <div className={`flex items-center justify-between py-2 ${indent ? 'pl-6' : ''} ${bold ? 'border-t border-white/20 pt-3 mt-2' : ''}`}>
      <div className="flex items-center gap-2 text-gray-400">
        {icon && <span className="text-gray-500">{icon}</span>}
        <span className={bold ? 'font-bold text-white' : ''}>{label}</span>
      </div>
      <span className={`font-mono ${valueColor} ${bold ? 'font-bold text-lg' : ''}`}>
        {isExpense && value > 0 ? '-' : ''}{formatMoney(Math.abs(value))}
      </span>
    </div>
  );
};

const AdminAccounting: React.FC<AdminAccountingProps> = ({ 
  data,
  onRefresh,
  onAddExpense,
  isLoading = false
}) => {
  const [period, setPeriod] = useState<'today' | 'month' | 'all'>('all');
  
  const d = data || {
    totalRevenue: 0,
    revenueGross: 0,
    revenueThisMonth: 0,
    revenueToday: 0,
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
    ordersThisMonth: 0,
    ordersToday: 0,
    reservesUsed: 0,
    reservesAvailable: 0,
  };

  // Calculated metrics
  const grossProfit = d.totalRevenue - d.totalCogs;
  const operatingExpenses = d.totalAcquiringFees + d.totalReferralPayouts + d.totalReserves + d.totalReviewCashbacks + d.totalReplacementCosts;
  const operatingProfit = grossProfit - operatingExpenses;
  const grossMargin = d.totalRevenue > 0 ? (grossProfit / d.totalRevenue) * 100 : 0;
  const netMargin = d.totalRevenue > 0 ? (d.netProfit / d.totalRevenue) * 100 : 0;
  const avgOrderValue = d.totalOrders > 0 ? d.totalRevenue / d.totalOrders : 0;
  
  // Reserve calculation
  const reservesAccumulated = d.totalReserves;
  const reservesUsed = d.reservesUsed || d.totalOtherExpenses; // Use other_expenses as proxy for used reserves
  const reservesAvailable = reservesAccumulated - reservesUsed;

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
          <div className="flex bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
            {(['today', 'month', 'all'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-xs font-mono uppercase transition-colors ${
                  period === p 
                    ? 'bg-pandora-cyan text-black' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {p === 'today' ? 'Сегодня' : p === 'month' ? 'Месяц' : 'Всё время'}
              </button>
            ))}
          </div>
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
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 bg-[#0e0e0e] border border-white/10 rounded-sm hover:border-pandora-cyan transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={`text-gray-400 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
      </div>

      {/* Ключевые метрики */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase mb-2">
            <DollarSign size={14} />
            Выручка
          </div>
          <div className="text-2xl font-bold text-white font-mono">{formatMoney(d.totalRevenue)}</div>
          <div className="text-xs text-gray-500 mt-1">{d.totalOrders} заказов</div>
        </div>
        
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase mb-2">
            <TrendingUp size={14} />
            Валовая прибыль
          </div>
          <div className="text-2xl font-bold text-green-400 font-mono">{formatMoney(grossProfit)}</div>
          <div className="text-xs text-gray-500 mt-1">{formatPercent(grossMargin)} маржа</div>
        </div>
        
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase mb-2">
            <PiggyBank size={14} />
            Чистая прибыль
          </div>
          <div className={`text-2xl font-bold font-mono ${d.netProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatMoney(d.netProfit)}
          </div>
          <div className="text-xs text-gray-500 mt-1">{formatPercent(netMargin)} маржа</div>
        </div>
        
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
          <div className="flex items-center gap-2 text-gray-400 text-xs uppercase mb-2">
            <TrendingDown size={14} />
            Все расходы
          </div>
          <div className="text-2xl font-bold text-red-400 font-mono">
            {formatMoney(d.totalCogs + operatingExpenses + d.totalOtherExpenses)}
          </div>
          <div className="text-xs text-gray-500 mt-1">COGS + OpEx</div>
        </div>
      </div>

      {/* P&L Statement */}
      <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-gray-500 font-mono mb-4 pb-2 border-b border-white/10">
          Отчёт о финансовых результатах
        </h4>
        
        {/* Выручка */}
        <div className="mb-4">
          <div className="text-xs uppercase text-pandora-cyan font-mono mb-2">Выручка</div>
          <MetricRow 
            label="Валовая выручка" 
            value={d.revenueGross} 
            icon={<DollarSign size={14} />}
          />
          <MetricRow 
            label="Скидки" 
            value={d.totalDiscountsGiven} 
            isExpense 
            indent
            icon={<Percent size={14} />}
          />
          <MetricRow 
            label="Чистая выручка" 
            value={d.totalRevenue} 
            bold
          />
          {d.totalInsuranceRevenue > 0 && (
            <MetricRow 
              label="Доход от страховок" 
              value={d.totalInsuranceRevenue} 
              indent
              icon={<Shield size={14} />}
            />
          )}
        </div>

        {/* Себестоимость */}
        <div className="mb-4">
          <div className="text-xs uppercase text-pandora-cyan font-mono mb-2">Себестоимость</div>
          <MetricRow 
            label="Себестоимость товаров (COGS)" 
            value={d.totalCogs} 
            isExpense
            icon={<DollarSign size={14} />}
          />
          <MetricRow 
            label="Валовая прибыль" 
            value={grossProfit} 
            isProfit
            bold
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
          />
          <MetricRow 
            label="Реферальные выплаты (3 линии)" 
            value={d.totalReferralPayouts} 
            isExpense
            indent
            icon={<Users size={14} />}
          />
          <MetricRow 
            label="Кэшбэк за отзывы (5%)" 
            value={d.totalReviewCashbacks} 
            isExpense
            indent
            icon={<Star size={14} />}
          />
          <MetricRow 
            label="Страховые замены" 
            value={d.totalReplacementCosts} 
            isExpense
            indent
            icon={<Shield size={14} />}
          />
          <MetricRow 
            label="Резервы (маркетинг + непредв.)" 
            value={d.totalReserves} 
            isExpense
            indent
            icon={<PiggyBank size={14} />}
          />
          <MetricRow 
            label="Операционная прибыль" 
            value={operatingProfit} 
            isProfit
            bold
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
            />
          </div>
        )}

        {/* Чистая прибыль */}
        <div className="pt-4 border-t-2 border-pandora-cyan/30">
          <MetricRow 
            label="ЧИСТАЯ ПРИБЫЛЬ" 
            value={d.netProfit} 
            isProfit
            bold
          />
        </div>
      </div>

      {/* Резервы */}
      <div className="bg-[#0e0e0e] border border-yellow-500/30 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-yellow-400 font-mono mb-4 pb-2 border-b border-white/10 flex items-center gap-2">
          <PiggyBank size={14} />
          Резервы (8% от выручки)
        </h4>
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div className="text-xs text-gray-500 uppercase">Накоплено</div>
            <div className="text-lg font-mono text-yellow-400">{formatMoney(reservesAccumulated)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Использовано</div>
            <div className="text-lg font-mono text-red-400">{formatMoney(reservesUsed)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase">Доступно</div>
            <div className={`text-lg font-mono ${reservesAvailable >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {formatMoney(reservesAvailable)}
            </div>
          </div>
        </div>
        <div className="text-xs text-gray-500">
          💡 Резервы = 5% маркетинг + 3% непредвиденные. При добавлении расхода с категорией "marketing" или "unforeseen" он списывается из резервов.
        </div>
      </div>

      {/* Обязательства */}
      <div className="bg-[#0e0e0e] border border-red-500/30 p-6 rounded-sm">
        <h4 className="text-xs uppercase text-red-400 font-mono mb-4 pb-2 border-b border-white/10">
          Обязательства (деньги пользователей)
        </h4>
        <MetricRow 
          label="Балансы пользователей" 
          value={d.totalUserBalances} 
          isExpense
        />
        <MetricRow 
          label="Ожидают вывода" 
          value={d.pendingWithdrawals} 
          isExpense
        />
        <MetricRow 
          label="Всего обязательств" 
          value={d.totalUserBalances + d.pendingWithdrawals} 
          isExpense
          bold
        />
      </div>

      {/* Быстрая статистика */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div className="bg-[#0e0e0e] border border-white/10 p-3 rounded-sm">
          <div className="text-gray-500 uppercase">Средний чек</div>
          <div className="text-white font-mono mt-1">{formatMoney(avgOrderValue)}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-3 rounded-sm">
          <div className="text-gray-500 uppercase">COGS на заказ</div>
          <div className="text-white font-mono mt-1">{formatMoney(d.totalOrders > 0 ? d.totalCogs / d.totalOrders : 0)}</div>
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
