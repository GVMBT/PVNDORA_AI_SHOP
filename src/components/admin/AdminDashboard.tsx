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
  // Use provided stats or default values
  const displayStats = stats || {
    totalRevenue: 4200000,
    ordersToday: 142,
    ordersWeek: 0,
    ordersMonth: 0,
    activeUsers: 8920,
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard 
          label="Total Revenue" 
          value={`₽ ${(displayStats.totalRevenue / 1000000).toFixed(1)}M`} 
          trend="+12%" 
          icon={<DollarSign size={20} />} 
        />
        <StatCard 
          label="Active Orders" 
          value={String(displayStats.ordersToday)} 
          trend="+5%" 
          icon={<ShoppingBag size={20} />} 
        />
        <StatCard 
          label="Total Users" 
          value={displayStats.activeUsers.toLocaleString()} 
          trend="+24" 
          icon={<Users size={20} />} 
        />
        <StatCard 
          label="Open Tickets" 
          value="15" 
          trend="-2" 
          isNegative={false} 
          icon={<LifeBuoy size={20} />} 
        />
      </div>
      {/* Charts placeholder */}
      <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm h-64 flex items-end justify-between gap-2">
        {[...Array(12)].map((_, i) => (
          <div 
            key={i} 
            className="flex-1 bg-white/5 hover:bg-pandora-cyan transition-colors" 
            style={{ height: `${Math.random() * 80 + 20}%` }} 
          />
        ))}
      </div>
    </div>
  );
};

export default memo(AdminDashboard);


