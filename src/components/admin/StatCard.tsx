/**
 * StatCard Component
 *
 * Displays a statistic card with label, value, trend, and icon.
 */

import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type React from "react";
import { memo } from "react";

interface StatCardProps {
  label: string;
  value: string;
  trend?: string;
  icon: React.ReactNode;
  isNegative?: boolean;
  hideTrendComparison?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  trend,
  icon,
  isNegative = false,
  hideTrendComparison = false,
}) => (
  <div className="rounded-sm border border-white/10 bg-[#0e0e0e] p-4 transition-colors hover:border-white/20 md:p-6">
    <div className="mb-2 flex items-start justify-between">
      <div className="font-mono text-[10px] text-gray-500 uppercase">{label}</div>
      <div className="text-gray-600">{icon}</div>
    </div>
    <div
      className={`font-bold text-xl md:text-2xl ${isNegative ? "text-amber-400" : "text-white"} mb-2`}
    >
      {value}
    </div>
    {trend && (
      <div
        className={`font-bold text-xs ${isNegative ? "text-amber-500/70" : "text-green-500"} flex items-center gap-1`}
      >
        {!hideTrendComparison &&
          (isNegative ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />)}
        {trend}{" "}
        {!hideTrendComparison && (
          <span className="hidden font-normal text-gray-600 md:inline">vs last week</span>
        )}
      </div>
    )}
  </div>
);

export default memo(StatCard);
