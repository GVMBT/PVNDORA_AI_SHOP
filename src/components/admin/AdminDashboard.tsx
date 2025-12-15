/**
 * AdminDashboard Component
 * 
 * Dashboard view showing statistics and charts.
 */

import React, { memo } from 'react';
import { DollarSign, ShoppingBag, Users, LifeBuoy } from 'lucide-react';
import StatCard from './StatCard';
import type { AdminStats } from './types';

interface AdminDashboardProps {
  stats?: AdminStats;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ stats }) => {
  // Use provided stats or default to 0 (no mocks)
  const displayStats = stats || {
    totalRevenue: 0,
    ordersToday: 0,
    ordersWeek: 0,
    ordersMonth: 0,
    activeUsers: 0,
    openTickets: 0,
    revenueByDay: []
  };

  // Format revenue for display
  const formatRevenue = (revenue: number): string => {
    if (revenue >= 1000000) {
      return `₽ ${(revenue / 1000000).toFixed(1)}M`;
    } else if (revenue >= 1000) {
      return `₽ ${(revenue / 1000).toFixed(1)}K`;
    }
    return `₽ ${revenue.toFixed(0)}`;
  };

  // Prepare chart data from revenue_by_day
  const chartData = displayStats.revenueByDay || [];
  const maxRevenue = chartData.length > 0 
    ? Math.max(...chartData.map(d => d.amount))
    : 1; // Avoid division by zero

  // Generate 12 bars (fill missing days with 0)
  const chartBars = Array.from({ length: 12 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (11 - i));
    const dateStr = date.toISOString().split('T')[0];
    const dayData = chartData.find(d => d.date === dateStr);
    const amount = dayData?.amount || 0;
    const heightPercent = maxRevenue > 0 ? (amount / maxRevenue) * 100 : 0;
    return { date: dateStr, amount, height: Math.max(heightPercent, 5) }; // Min 5% for visibility
  });

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          label="Total Revenue" 
          value={formatRevenue(displayStats.totalRevenue)} 
          trend="" 
          icon={<DollarSign size={20} />} 
        />
        <StatCard 
          label="Active Orders" 
          value={String(displayStats.ordersToday)} 
          trend="" 
          icon={<ShoppingBag size={20} />} 
        />
        <StatCard 
          label="Total Users" 
          value={displayStats.activeUsers.toLocaleString()} 
          trend="" 
          icon={<Users size={20} />} 
        />
        <StatCard 
          label="Open Tickets" 
          value={String(displayStats.openTickets || 0)} 
          trend="" 
          isNegative={false} 
          icon={<LifeBuoy size={20} />} 
        />
      </div>
      {/* Revenue Chart */}
      <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm h-64 flex items-end justify-between gap-2">
        {chartBars.map((bar, i) => (
          <div 
            key={i} 
            className="flex-1 bg-white/5 hover:bg-pandora-cyan transition-colors rounded-t-sm relative group" 
            style={{ height: `${bar.height}%` }}
            title={`${bar.date}: ₽${bar.amount.toFixed(0)}`}
          />
        ))}
      </div>
    </div>
  );
};

export default memo(AdminDashboard);








