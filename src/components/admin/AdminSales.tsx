/**
 * AdminSales Component
 * 
 * Sales and orders management view.
 */

import React, { useState, useMemo, memo } from 'react';
import { Search } from 'lucide-react';
import StatusBadge from './StatusBadge';
import type { OrderData } from './types';

interface AdminSalesProps {
  orders: OrderData[];
}

const AdminSales: React.FC<AdminSalesProps> = ({ orders }) => {
  const [orderSearch, setOrderSearch] = useState('');

  const filteredOrders = useMemo(() => {
    return orders.filter(o => 
      o.id.toLowerCase().includes(orderSearch.toLowerCase()) || 
      o.user.toLowerCase().includes(orderSearch.toLowerCase())
    );
  }, [orders, orderSearch]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <h3 className="font-display font-bold text-white uppercase text-lg">Transactions</h3>
        <div className="relative w-full md:w-auto">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
          <input 
            type="text" 
            placeholder="Search Order ID or User..." 
            value={orderSearch}
            onChange={(e) => setOrderSearch(e.target.value)}
            className="w-full md:w-64 bg-[#0e0e0e] border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none" 
          />
        </div>
      </div>

      <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-white/5 text-gray-400 uppercase">
            <tr>
              <th className="p-4">Order ID</th>
              <th className="p-4">User</th>
              <th className="p-4">Product</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            {filteredOrders.map(o => (
              <tr key={o.id} className="hover:bg-white/5 transition-colors cursor-pointer">
                <td className="p-4 font-bold text-pandora-cyan">{o.id}</td>
                <td className="p-4 text-gray-400">{o.user}</td>
                <td className="p-4 font-bold text-white">{o.product}</td>
                <td className="p-4">
                  <StatusBadge status={o.status} />
                </td>
                <td className="p-4 text-right text-gray-500">{o.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Orders */}
      <div className="md:hidden space-y-4">
        {filteredOrders.map(o => (
          <div key={o.id} className="bg-[#0e0e0e] border border-white/10 p-4 space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-bold text-pandora-cyan text-sm">{o.id}</span>
              <span className="text-[10px] text-gray-500">{o.date}</span>
            </div>
            <div className="text-sm text-white font-bold">{o.product}</div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">{o.user}</span>
              <StatusBadge status={o.status} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default memo(AdminSales);
