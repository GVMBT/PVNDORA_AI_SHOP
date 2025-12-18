/**
 * AdminHeader Component
 * 
 * Header for admin panel main content area.
 */

import React, { memo } from 'react';
import { Settings } from 'lucide-react';
import type { AdminView } from './types';

interface AdminHeaderProps {
  currentView: AdminView;
}

const AdminHeader: React.FC<AdminHeaderProps> = ({ currentView }) => {
  return (
    <div className="hidden md:flex h-20 border-b border-white/10 justify-between items-center px-8 bg-[#050505] sticky top-0 z-30">
      <div>
        <h2 className="text-2xl font-display font-bold text-white uppercase">
          {currentView}
        </h2>
        <div className="text-[10px] font-mono text-gray-500">
          LAST_LOGIN: 2025.10.02 // 14:00
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-xs font-bold text-white">AdminUser_01</div>
          <div className="text-[10px] text-green-500 font-mono">ONLINE</div>
        </div>
        <div className="w-10 h-10 bg-red-900/20 border border-red-500/50 rounded-sm flex items-center justify-center text-red-500">
          <Settings size={20} />
        </div>
      </div>
    </div>
  );
};

export default memo(AdminHeader);

















