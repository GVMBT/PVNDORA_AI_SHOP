/**
 * AdminDashboard Component
 *
 * Операционная панель — быстрые действия и статусы.
 * Финансы вынесены в Accounting.
 */

import { Clock, LifeBuoy, Package, ShoppingBag, TrendingUp, Users } from "lucide-react";
import type React from "react";
import { memo } from "react";
import StatCard from "./StatCard";
import type { AdminStats } from "./types";

interface AdminDashboardProps {
  stats?: AdminStats;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ stats }) => {
  const displayStats = stats || {
    totalRevenue: 0,
    ordersToday: 0,
    ordersWeek: 0,
    ordersMonth: 0,
    totalUsers: 0,
    pendingOrders: 0,
    openTickets: 0,
    revenueByDay: [],
    totalUserBalances: 0,
    pendingWithdrawals: 0,
  };

  // Prepare chart data from revenue_by_day
  const chartData = displayStats.revenueByDay || [];
  const maxRevenue = chartData.length > 0 ? Math.max(...chartData.map((d) => d.amount)) : 1;

  const chartBars = Array.from({ length: 12 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (11 - i));
    const dateStr = date.toISOString().split("T")[0];
    const dayData = chartData.find((d) => d.date === dateStr);
    const amount = dayData?.amount || 0;
    const heightPercent = maxRevenue > 0 ? (amount / maxRevenue) * 100 : 0;
    return { date: dateStr, amount, height: Math.max(heightPercent, 5) };
  });

  return (
    <div className="space-y-6">
      {/* Операционные метрики */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Заказов сегодня"
          value={String(displayStats.ordersToday || 0)}
          trend={`${displayStats.ordersWeek || 0} за неделю`}
          icon={<ShoppingBag size={20} />}
        />
        <StatCard
          label="Ожидают выдачи"
          value={String(displayStats.pendingOrders || 0)}
          trend="Требуют внимания"
          isNegative={displayStats.pendingOrders > 0}
          icon={<Package size={20} />}
        />
        <StatCard
          label="Пользователей"
          value={displayStats.totalUsers.toLocaleString()}
          trend="Всего зарегистрировано"
          icon={<Users size={20} />}
        />
        <StatCard
          label="Открытые тикеты"
          value={String(displayStats.openTickets || 0)}
          trend="Требуют ответа"
          isNegative={displayStats.openTickets > 0}
          icon={<LifeBuoy size={20} />}
        />
      </div>

      {/* График активности */}
      <div className="bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
          <span className="text-xs font-mono text-gray-400 uppercase">Выручка за 12 дней</span>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <TrendingUp size={12} />
            <span>${displayStats.totalRevenue?.toFixed(0) || 0} всего</span>
          </div>
        </div>
        <div className="p-6 h-48 flex items-end justify-between gap-2">
          {chartBars.map((bar) => (
            <div
              key={bar.date}
              className="flex-1 bg-white/5 hover:bg-pandora-cyan transition-colors rounded-t-sm relative group cursor-pointer"
              style={{ height: `${bar.height}%` }}
            >
              <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-black/90 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                {bar.date.slice(5)}: ${bar.amount.toFixed(0)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Быстрые действия */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm hover:border-pandora-cyan/50 transition-colors cursor-pointer">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-pandora-cyan/10 rounded-sm flex items-center justify-center">
              <Package size={18} className="text-pandora-cyan" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">Каталог</div>
              <div className="text-xs text-gray-500">Управление товарами</div>
            </div>
          </div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm hover:border-pandora-cyan/50 transition-colors cursor-pointer">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-500/10 rounded-sm flex items-center justify-center">
              <TrendingUp size={18} className="text-green-500" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">Бухгалтерия</div>
              <div className="text-xs text-gray-500">P&L и финансы</div>
            </div>
          </div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4 rounded-sm hover:border-pandora-cyan/50 transition-colors cursor-pointer">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-500/10 rounded-sm flex items-center justify-center">
              <Clock size={18} className="text-red-500" />
            </div>
            <div>
              <div className="text-sm font-bold text-white">Поддержка</div>
              <div className="text-xs text-gray-500">{displayStats.openTickets || 0} тикетов</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(AdminDashboard);
