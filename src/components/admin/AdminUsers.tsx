/**
 * AdminUsers Component
 * 
 * Users management view - displays all users with management actions.
 */

import React, { useState, memo, useMemo } from 'react';
import { Search, Ban, DollarSign, AlertTriangle } from 'lucide-react';
import type { UserData } from './types';

interface AdminUsersProps {
  users: UserData[];
  onBanUser?: (userId: number, ban: boolean) => void;
  onUpdateBalance?: (userId: number, amount: number) => void;
}

const AdminUsers: React.FC<AdminUsersProps> = ({
  users,
  onBanUser,
  onUpdateBalance,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<'ALL' | 'USER' | 'VIP' | 'ADMIN'>('ALL');

  // Filter users
  const filteredUsers = useMemo(() => {
    let result = users;

    // Search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(u => 
        u.username.toLowerCase().includes(query) ||
        u.id.toString().includes(query)
      );
    }

    // Role filter
    if (roleFilter !== 'ALL') {
      result = result.filter(u => u.role === roleFilter);
    }

    return result;
  }, [users, searchQuery, roleFilter]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'ADMIN':
        return <span className="text-[10px] px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30">ADMIN</span>;
      case 'VIP':
        return <span className="text-[10px] px-2 py-0.5 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">VIP</span>;
      default:
        return <span className="text-[10px] px-2 py-0.5 bg-white/5 text-gray-400 border border-white/10">USER</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 bg-[#0e0e0e] border border-white/10 p-4 rounded-sm">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by username or ID..." 
            className="w-full bg-black border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none" 
          />
        </div>
        <div className="flex gap-2">
          {(['ALL', 'USER', 'VIP', 'ADMIN'] as const).map(role => (
            <button
              key={role}
              onClick={() => setRoleFilter(role)}
              className={`px-3 py-2 text-[10px] font-bold uppercase border transition-colors ${
                roleFilter === role
                  ? 'bg-pandora-cyan text-black border-pandora-cyan'
                  : 'bg-transparent text-gray-400 border-white/20 hover:border-white/40'
              }`}
            >
              {role}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Total Users</div>
          <div className="text-2xl font-bold text-white">{users.length}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">VIP Users</div>
          <div className="text-2xl font-bold text-yellow-400">{users.filter(u => u.role === 'VIP').length}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Banned</div>
          <div className="text-2xl font-bold text-red-400">{users.filter(u => u.isBanned).length}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Active Today</div>
          <div className="text-2xl font-bold text-green-400">—</div>
        </div>
      </div>

      {/* Users Table - Desktop */}
      <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-white/5 text-gray-400 uppercase">
            <tr>
              <th className="p-4">Username</th>
              <th className="p-4">Role</th>
              <th className="p-4">Balance</th>
              <th className="p-4">Orders</th>
              <th className="p-4">Total Spent</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-500">
                  No users found
                </td>
              </tr>
            ) : (
              filteredUsers.map(u => (
                <tr key={u.id} className={`hover:bg-white/5 transition-colors ${u.isBanned ? 'opacity-50' : ''}`}>
                  <td className="p-4">
                    <a 
                      href={`https://t.me/${u.username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-bold text-white hover:text-pandora-cyan transition-colors"
                    >
                      @{u.username}
                    </a>
                    <div className="text-[10px] text-gray-600">ID: {u.id}</div>
                  </td>
                  <td className="p-4">
                    {getRoleBadge(u.role)}
                  </td>
                  <td className="p-4 text-pandora-cyan">
                    {formatCurrency(u.balance)}
                  </td>
                  <td className="p-4">
                    {u.purchases}
                  </td>
                  <td className="p-4">
                    {formatCurrency(u.spent)}
                  </td>
                  <td className="p-4">
                    {u.isBanned ? (
                      <span className="text-[10px] px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30">
                        BANNED
                      </span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 bg-green-500/20 text-green-400 border border-green-500/30">
                        ACTIVE
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button 
                        onClick={() => onUpdateBalance?.(u.id, 0)}
                        className="p-1.5 border border-white/10 hover:border-pandora-cyan hover:text-pandora-cyan transition-colors"
                        title="Adjust Balance"
                      >
                        <DollarSign size={14} />
                      </button>
                      <button 
                        onClick={() => onBanUser?.(u.id, !u.isBanned)}
                        className={`p-1.5 border transition-colors ${
                          u.isBanned 
                            ? 'border-green-500/30 text-green-400 hover:border-green-500' 
                            : 'border-red-500/30 text-red-400 hover:border-red-500'
                        }`}
                        title={u.isBanned ? 'Unban User' : 'Ban User'}
                      >
                        <Ban size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Users Cards - Mobile */}
      <div className="md:hidden space-y-4">
        {filteredUsers.length === 0 ? (
          <div className="bg-[#0e0e0e] border border-white/10 p-8 text-center text-gray-500">
            No users found
          </div>
        ) : (
          filteredUsers.map(u => (
            <div 
              key={u.id} 
              className={`bg-[#0e0e0e] border border-white/10 p-4 ${u.isBanned ? 'opacity-50' : ''}`}
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <a 
                    href={`https://t.me/${u.username}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-bold text-white hover:text-pandora-cyan transition-colors"
                  >
                    @{u.username}
                  </a>
                  <div className="text-[10px] text-gray-600">ID: {u.id}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {getRoleBadge(u.role)}
                  {u.isBanned && (
                    <span className="text-[10px] px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30">
                      BANNED
                    </span>
                  )}
                </div>
              </div>
              
              <div className="grid grid-cols-3 gap-2 text-center mb-3">
                <div>
                  <div className="text-[10px] text-gray-500">Balance</div>
                  <div className="text-sm font-bold text-pandora-cyan">{formatCurrency(u.balance)}</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500">Orders</div>
                  <div className="text-sm font-bold text-white">{u.purchases}</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500">Spent</div>
                  <div className="text-sm font-bold text-white">{formatCurrency(u.spent)}</div>
                </div>
              </div>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => onUpdateBalance?.(u.id, 0)}
                  className="flex-1 flex items-center justify-center gap-2 py-2 text-[10px] bg-white/5 hover:bg-pandora-cyan hover:text-black transition-colors"
                >
                  <DollarSign size={12} /> Balance
                </button>
                <button 
                  onClick={() => onBanUser?.(u.id, !u.isBanned)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-[10px] transition-colors ${
                    u.isBanned 
                      ? 'bg-green-500/20 text-green-400 hover:bg-green-500 hover:text-black' 
                      : 'bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-black'
                  }`}
                >
                  <Ban size={12} /> {u.isBanned ? 'Unban' : 'Ban'}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default memo(AdminUsers);

