/**
 * AdminNavItem Component
 * 
 * Navigation item for admin sidebar.
 */

import React, { memo } from 'react';

interface AdminNavItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  collapsed: boolean;
}

const AdminNavItem: React.FC<AdminNavItemProps> = ({ 
  icon, 
  label, 
  active, 
  onClick, 
  collapsed 
}) => (
  <button 
    onClick={onClick}
    className={`flex items-center gap-3 w-full p-3 rounded-sm transition-all relative group ${
      active ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-white hover:bg-white/5'
    } ${collapsed ? 'justify-center' : ''}`}
  >
    {active && <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500 rounded-l-sm" />}
    {icon}
    {!collapsed && <span className="text-xs font-bold uppercase tracking-wide">{label}</span>}
  </button>
);

export default memo(AdminNavItem);





































