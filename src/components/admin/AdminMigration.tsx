/**
 * AdminMigration Component
 *
 * Shows discount bot migration statistics and analytics.
 */

import { ArrowUpRight, DollarSign, ShoppingBag, Tag, TrendingUp, Users } from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { useAdminMigrationApi } from "../../hooks/api/useAdminMigrationApi";
import StatCard from "./StatCard";

const AdminMigration: React.FC = () => {
  const { stats, trend, topProducts, getStats, getTrend, getTopProducts, loading } =
    useAdminMigrationApi();
  const [period, setPeriod] = useState(30);

  useEffect(() => {
    const fetchData = async () => {
      await Promise.all([getStats(period), getTrend(14), getTopProducts(10)]);
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
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <div className="mx-auto mb-2 h-8 w-8 animate-spin rounded-full border-2 border-pandora-cyan border-t-transparent" />
          <div className="text-gray-500 text-sm">Loading migration data...</div>
        </div>
      </div>
    );
  }

  if (!stats) {
    return <div className="py-12 text-center text-gray-500">No migration data available</div>;
  }

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex items-center justify-between">
        <h2 className="font-bold text-white text-xl">Migration Analytics</h2>
        <div className="flex gap-2">
          {[7, 30, 90].map((days) => (
            <button
              className={`rounded-sm px-3 py-1 text-sm transition-colors ${
                period === days
                  ? "bg-pandora-cyan font-bold text-black"
                  : "bg-white/5 text-gray-400 hover:bg-white/10"
              }`}
              key={days}
              onClick={() => setPeriod(days)}
              type="button"
            >
              {days}d
            </button>
          ))}
        </div>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard
          icon={<Users size={20} />}
          label="Discount Users"
          value={stats.total_discount_users.toLocaleString()}
        />
        <StatCard
          icon={<ArrowUpRight size={20} />}
          label="Migrated Users"
          trend={`${formatPercent(stats.migration_rate)} migration rate`}
          value={stats.migrated_users.toLocaleString()}
        />
        <StatCard
          icon={<ShoppingBag size={20} />}
          label="Discount Orders"
          value={stats.discount_orders.toLocaleString()}
        />
        <StatCard
          icon={<DollarSign size={20} />}
          label="Discount Revenue"
          value={formatRevenue(stats.discount_revenue)}
        />
      </div>

      {/* Migration Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <StatCard
          icon={<TrendingUp size={20} />}
          label="PVNDORA Orders"
          trend="From discount users"
          value={stats.pvndora_orders_from_discount.toLocaleString()}
        />
        <StatCard
          icon={<Tag size={20} />}
          label="Promos Generated"
          value={stats.promos_generated.toLocaleString()}
        />
        <StatCard
          icon={<Tag size={20} />}
          label="Promo Conversion"
          trend={`${stats.promos_used} used`}
          value={formatPercent(stats.promo_conversion_rate)}
        />
      </div>

      {/* Trend Chart */}
      {trend.length > 0 && (
        <div className="rounded-sm border border-white/10 bg-[#0e0e0e] p-6">
          <h3 className="mb-4 font-bold text-lg text-white">Migration Trend (14 days)</h3>
          <div className="flex h-64 items-end justify-between gap-2">
            {trend.map((day) => {
              const maxOrders = Math.max(
                ...trend.map((d) => Math.max(d.discount_orders, d.pvndora_orders || 0))
              );
              const discountHeight = maxOrders > 0 ? (day.discount_orders / maxOrders) * 100 : 0;
              const pvndoraHeight =
                maxOrders > 0 ? ((day.pvndora_orders || 0) / maxOrders) * 100 : 0;

              return (
                <div className="flex flex-1 flex-col items-center gap-1" key={day.date}>
                  <div className="flex w-full flex-col gap-1" style={{ height: "200px" }}>
                    <div
                      className="w-full rounded-t-sm bg-orange-500/50 transition-colors hover:bg-orange-500"
                      style={{ height: `${Math.max(discountHeight, 5)}%` }}
                      title={`${day.date}: ${day.discount_orders} discount orders`}
                    />
                    <div
                      className="w-full rounded-t-sm bg-pandora-cyan/50 transition-colors hover:bg-pandora-cyan"
                      style={{ height: `${Math.max(pvndoraHeight, 5)}%` }}
                      title={`${day.date}: ${day.pvndora_orders || 0} PVNDORA orders`}
                    />
                  </div>
                  <div className="mt-1 font-mono text-[10px] text-gray-500">
                    {new Date(day.date).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    })}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 flex gap-4 text-gray-400 text-xs">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 bg-orange-500/50" />
              <span>Discount Orders</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 bg-pandora-cyan/50" />
              <span>PVNDORA Orders (from discount users)</span>
            </div>
          </div>
        </div>
      )}

      {/* Top Products */}
      {topProducts.length > 0 && (
        <div className="rounded-sm border border-white/10 bg-[#0e0e0e] p-6">
          <h3 className="mb-4 font-bold text-lg text-white">Top Migrating Products</h3>
          <div className="space-y-2">
            {topProducts.map((product, i) => (
              <div
                className="flex items-center justify-between rounded-sm bg-white/5 p-3 transition-colors hover:bg-white/10"
                key={product.product_id}
              >
                <div className="flex items-center gap-3">
                  <div className="w-6 font-mono text-gray-500 text-sm">#{i + 1}</div>
                  <div>
                    <div className="font-medium text-white">{product.name}</div>
                    <div className="text-gray-500 text-xs">{product.category}</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-pandora-cyan">{product.migration_orders}</div>
                  <div className="text-gray-500 text-xs">orders</div>
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
