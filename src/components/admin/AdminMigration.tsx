/**
 * AdminMigration Component
 * 
 * Shows discount bot migration statistics and analytics.
 */

import React, { useEffect, useState } from 'react';
import { useAdminMigrationApi, MigrationStats, MigrationTrend, TopMigratingProduct } from '../../hooks/api/useAdminMigrationApi';
import { ArrowUpRight, Users, ShoppingBag, DollarSign, TrendingUp, Tag } from 'lucide-react';
import StatCard from './StatCard';

const AdminMigration: React.FC = () => {
  const { stats, trend, topProducts, getStats, getTrend, getTopProducts, loading } = useAdminMigrationApi();
  const [period, setPeriod] = useState(30);

  useEffect(() => {
    const fetchData = async () => {
      await Promise.all([
        getStats(period),
        getTrend(14),
        getTopProducts(10)
      ]);
    };
    fetchData();
  }, [period, getStats, getTrend, getTopProducts]);

  const formatRevenue = (revenue: number): string => {
    if (revenue >= 1000) {
      return `$ ${(revenue / 1000).toFixed(1)}K`;
    }
    return `$ ${revenue.toFixed(0)}`;
  };

  const formatPercent = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          <div className="text-sm text-gray-500">Loading migration data...</div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12 text-gray-500">
        No migration data available
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Migration Analytics</h2>
        <div className="flex gap-2">
          {[7, 30, 90].map((days) => (
            <button
              key={days}
              onClick={() => setPeriod(days)}
              className={`px-3 py-1 text-sm rounded-sm transition-colors ${
                period === days
                  ? 'bg-pandora-cyan text-black font-bold'
                  : 'bg-white/5 text-gray-400 hover:bg-white/10'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Discount Users"
          value={stats.total_discount_users.toLocaleString()}
          icon={<Users size={20} />}
        />
        <StatCard
          label="Migrated Users"
          value={stats.migrated_users.toLocaleString()}
          trend={`${formatPercent(stats.migration_rate)} migration rate`}
          icon={<ArrowUpRight size={20} />}
        />
        <StatCard
          label="Discount Orders"
          value={stats.discount_orders.toLocaleString()}
          icon={<ShoppingBag size={20} />}
        />
        <StatCard
          label="Discount Revenue"
          value={formatRevenue(stats.discount_revenue)}
          icon={<DollarSign size={20} />}
        />
      </div>

      {/* Migration Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          label="PVNDORA Orders"
          value={stats.pvndora_orders_from_discount.toLocaleString()}
          trend="From discount users"
          icon={<TrendingUp size={20} />}
        />
        <StatCard
          label="Promos Generated"
          value={stats.promos_generated.toLocaleString()}
          icon={<Tag size={20} />}
        />
        <StatCard
          label="Promo Conversion"
          value={formatPercent(stats.promo_conversion_rate)}
          trend={`${stats.promos_used} used`}
          icon={<Tag size={20} />}
        />
      </div>

      {/* Trend Chart */}
      {trend.length > 0 && (
        <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm">
          <h3 className="text-lg font-bold text-white mb-4">Migration Trend (14 days)</h3>
          <div className="h-64 flex items-end justify-between gap-2">
            {trend.map((day, i) => {
              const maxOrders = Math.max(
                ...trend.map(d => Math.max(d.discount_orders, d.pvndora_orders || 0))
              );
              const discountHeight = maxOrders > 0 ? (day.discount_orders / maxOrders) * 100 : 0;
              const pvndoraHeight = maxOrders > 0 ? ((day.pvndora_orders || 0) / maxOrders) * 100 : 0;
              
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex flex-col gap-1" style={{ height: '200px' }}>
                    <div
                      className="w-full bg-orange-500/50 hover:bg-orange-500 transition-colors rounded-t-sm"
                      style={{ height: `${Math.max(discountHeight, 5)}%` }}
                      title={`${day.date}: ${day.discount_orders} discount orders`}
                    />
                    <div
                      className="w-full bg-pandora-cyan/50 hover:bg-pandora-cyan transition-colors rounded-t-sm"
                      style={{ height: `${Math.max(pvndoraHeight, 5)}%` }}
                      title={`${day.date}: ${day.pvndora_orders || 0} PVNDORA orders`}
                    />
                  </div>
                  <div className="text-[10px] text-gray-500 font-mono mt-1">
                    {new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex gap-4 mt-4 text-xs text-gray-400">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-orange-500/50" />
              <span>Discount Orders</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-pandora-cyan/50" />
              <span>PVNDORA Orders (from discount users)</span>
            </div>
          </div>
        </div>
      )}

      {/* Top Products */}
      {topProducts.length > 0 && (
        <div className="bg-[#0e0e0e] border border-white/10 p-6 rounded-sm">
          <h3 className="text-lg font-bold text-white mb-4">Top Migrating Products</h3>
          <div className="space-y-2">
            {topProducts.map((product, i) => (
              <div
                key={product.product_id}
                className="flex items-center justify-between p-3 bg-white/5 rounded-sm hover:bg-white/10 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="text-gray-500 font-mono text-sm w-6">#{i + 1}</div>
                  <div>
                    <div className="text-white font-medium">{product.name}</div>
                    <div className="text-xs text-gray-500">{product.category}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-pandora-cyan font-bold">{product.migration_orders}</div>
                  <div className="text-xs text-gray-500">orders</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminMigration;
