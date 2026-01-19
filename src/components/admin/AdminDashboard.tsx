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
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          icon={<ShoppingBag size={20} />}
          label="Заказов сегодня"
          trend={`${displayStats.ordersWeek || 0} за неделю`}
          value={String(displayStats.ordersToday || 0)}
        />
        <StatCard
          icon={<Package size={20} />}
          isNegative={displayStats.pendingOrders > 0}
          label="Ожидают выдачи"
          trend="Требуют внимания"
          value={String(displayStats.pendingOrders || 0)}
        />
        <StatCard
          icon={<Users size={20} />}
          label="Пользователей"
          trend="Всего зарегистрировано"
          value={displayStats.totalUsers.toLocaleString()}
        />
        <StatCard
          icon={<LifeBuoy size={20} />}
          isNegative={displayStats.openTickets > 0}
          label="Открытые тикеты"
          trend="Требуют ответа"
          value={String(displayStats.openTickets || 0)}
        />
      </div>

      {/* График активности */}
      <div className="overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e]">
        <div className="flex items-center justify-between border-white/10 border-b px-4 py-3">
          <span className="font-mono text-gray-400 text-xs uppercase">Выручка за 12 дней</span>
          <div className="flex items-center gap-2 text-gray-500 text-xs">
            <TrendingUp size={12} />
            <span>${displayStats.totalRevenue?.toFixed(0) || 0} всего</span>
          </div>
        </div>
        <div className="flex h-48 items-end justify-between gap-2 p-6">
          {chartBars.map((bar) => (
            <div
              className="group relative flex-1 cursor-pointer rounded-t-sm bg-white/5 transition-colors hover:bg-pandora-cyan"
              key={bar.date}
              style={{ height: `${bar.height}%` }}
            >
              <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 -translate-x-1/2 whitespace-nowrap rounded bg-black/90 px-2 py-1 text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100">
                {bar.date.slice(5)}: ${bar.amount.toFixed(0)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Быстрые действия */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <div className="cursor-pointer rounded-sm border border-white/10 bg-[#0e0e0e] p-4 transition-colors hover:border-pandora-cyan/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-pandora-cyan/10">
              <Package className="text-pandora-cyan" size={18} />
            </div>
            <div>
              <div className="font-bold text-sm text-white">Каталог</div>
              <div className="text-gray-500 text-xs">Управление товарами</div>
            </div>
          </div>
        </div>
        <div className="cursor-pointer rounded-sm border border-white/10 bg-[#0e0e0e] p-4 transition-colors hover:border-pandora-cyan/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-green-500/10">
              <TrendingUp className="text-green-500" size={18} />
            </div>
            <div>
              <div className="font-bold text-sm text-white">Бухгалтерия</div>
              <div className="text-gray-500 text-xs">P&L и финансы</div>
            </div>
          </div>
        </div>
        <div className="cursor-pointer rounded-sm border border-white/10 bg-[#0e0e0e] p-4 transition-colors hover:border-pandora-cyan/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-sm bg-red-500/10">
              <Clock className="text-red-500" size={18} />
            </div>
            <div>
              <div className="font-bold text-sm text-white">Поддержка</div>
              <div className="text-gray-500 text-xs">{displayStats.openTickets || 0} тикетов</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(AdminDashboard);
