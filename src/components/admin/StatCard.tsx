/**
 * StatCard Component
 * 
 * Displays a statistic card with label, value, trend, and icon.
 */

import React, { memo } from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string;
  trend: string;
  icon: React.ReactNode;
  isNegative?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ 
  label, 
  value, 
  trend, 
  icon, 
  isNegative = false 
}) => (
  <div className="bg-[#0e0e0e] border border-white/10 p-4 md:p-6 rounded-sm hover:border-white/20 transition-colors">
    <div className="flex justify-between items-start mb-2">
      <div className="text-[10px] text-gray-500 font-mono uppercase">{label}</div>
      <div className="text-gray-600">{icon}</div>
    </div>
    <div className="text-xl md:text-2xl font-bold text-white mb-2">{value}</div>
    <div className={`text-xs font-bold ${isNegative ? 'text-red-500' : 'text-green-500'} flex items-center gap-1`}>
      {isNegative ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}
      {trend} <span className="text-gray-600 font-normal hidden md:inline">vs last week</span>
    </div>
  </div>
);

export default memo(StatCard);


