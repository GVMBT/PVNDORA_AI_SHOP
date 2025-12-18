/**
 * AdminSidebar Component
 * 
 * Sidebar navigation for admin panel.
 */

import React, { memo } from 'react';
import { 
  LayoutDashboard, 
  Package, 
  BarChart3, 
  Users, 
  LifeBuoy, 
  LogOut, 
  Terminal, 
  Menu,
  Tag
} from 'lucide-react';
import AdminNavItem from './AdminNavItem';
import type { AdminView } from './types';

interface AdminSidebarProps {
  currentView: AdminView;
  isOpen: boolean;
  isCollapsed: boolean;
  onViewChange: (view: AdminView) => void;
  onToggleCollapse: () => void;
  onClose: () => void;
  onExit: () => void;
}

const AdminSidebar: React.FC<AdminSidebarProps> = ({
  currentView,
  isOpen,
  isCollapsed,
  onViewChange,
  onToggleCollapse,
  onClose,
  onExit,
}) => {
  return (
    <>
      {/* Mobile Header */}
      <div className="md:hidden h-16 border-b border-white/10 flex items-center justify-between px-4 bg-[#050505] z-50 relative">
        <div className="font-display font-bold text-white tracking-widest flex items-center gap-2">
          <Terminal className="text-red-500" size={18} /> ADMIN
        </div>
        <button 
          onClick={onClose} 
          className="text-white"
        >
          <Menu size={24} />
        </button>
      </div>

      {/* Sidebar */}
      <div className={`
        fixed md:static inset-0 z-40 bg-[#050505] border-r border-white/10 transition-transform duration-300 flex flex-col
        ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        ${isCollapsed ? 'md:w-20' : 'md:w-64'}
        w-64
      `}>
        <div 
          className="hidden md:flex h-20 items-center px-6 border-b border-white/10 cursor-pointer hover:bg-white/5 transition-colors"
          onClick={onToggleCollapse}
          title="Toggle Sidebar"
        >
          <Terminal className="text-red-500 mr-3 shrink-0" />
          {!isCollapsed && (
            <div className="overflow-hidden whitespace-nowrap">
              <div className="font-display font-bold text-lg tracking-widest text-white">ADMIN</div>
              <div className="text-[9px] font-mono text-red-500 uppercase">Root Access</div>
            </div>
          )}
        </div>
        
        <div className="flex-1 py-6 space-y-1 px-3 mt-16 md:mt-0">
          <AdminNavItem 
            icon={<LayoutDashboard size={18} />} 
            label="Dashboard" 
            active={currentView === 'dashboard'} 
            onClick={() => {
              onViewChange('dashboard');
              onClose();
            }} 
            collapsed={isCollapsed} 
          />
          <AdminNavItem 
            icon={<Package size={18} />} 
            label="Catalog & Stock" 
            active={currentView === 'catalog'} 
            onClick={() => {
              onViewChange('catalog');
              onClose();
            }} 
            collapsed={isCollapsed} 
          />
          <AdminNavItem 
            icon={<BarChart3 size={18} />} 
            label="Sales & Orders" 
            active={currentView === 'sales'} 
            onClick={() => {
              onViewChange('sales');
              onClose();
            }} 
            collapsed={isCollapsed} 
          />
          <AdminNavItem 
            icon={<Users size={18} />} 
            label="Users" 
            active={currentView === 'partners'} 
            onClick={() => {
              onViewChange('partners');
              onClose();
            }} 
            collapsed={isCollapsed} 
          />
          <AdminNavItem 
            icon={<LifeBuoy size={18} />} 
            label="Support" 
            active={currentView === 'support'} 
            onClick={() => {
              onViewChange('support');
              onClose();
            }} 
            collapsed={isCollapsed} 
          />
          <AdminNavItem 
            icon={<Tag size={18} />} 
            label="Promo Codes" 
            active={currentView === 'promo'} 
            onClick={() => {
              onViewChange('promo');
              onClose();
            }} 
            collapsed={isCollapsed} 
          />
        </div>

        <div className="p-4 border-t border-white/10">
          <button 
            onClick={onExit} 
            className={`flex items-center gap-3 w-full text-gray-500 hover:text-white transition-colors p-2 rounded-sm hover:bg-white/5 ${
              isCollapsed ? 'justify-center' : ''
            }`}
          >
            <LogOut size={18} />
            {!isCollapsed && <span className="text-sm font-bold uppercase">Exit System</span>}
          </button>
        </div>
      </div>
    </>
  );
};

export default memo(AdminSidebar);







