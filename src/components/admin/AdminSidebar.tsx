/**
 * AdminSidebar Component
 *
 * Sidebar navigation for admin panel.
 */

import {
  ArrowRightLeft,
  BarChart3,
  Calculator,
  Crown,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  Package,
  Tag,
  Terminal,
  Users,
  Wallet,
} from "lucide-react";
import type React from "react";
import { memo } from "react";
import AdminNavItem from "./AdminNavItem";
import type { AdminView } from "./types";

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
      <div className="relative z-50 flex h-16 items-center justify-between border-white/10 border-b bg-[#050505] px-4 md:hidden">
        <div className="flex items-center gap-2 font-bold font-display text-white tracking-widest">
          <Terminal className="text-red-500" size={18} /> ADMIN
        </div>
        <button className="text-white" onClick={onClose} type="button">
          <Menu size={24} />
        </button>
      </div>

      {/* Sidebar */}
      <div
        className={`fixed inset-0 z-40 flex flex-col border-white/10 border-r bg-[#050505] transition-transform duration-300 md:static ${isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        ${isCollapsed ? "md:w-20" : "md:w-64"}w-64`}
      >
        <button
          className="hidden h-20 w-full cursor-pointer items-center border-white/10 border-b px-6 text-left transition-colors hover:bg-white/5 md:flex"
          onClick={onToggleCollapse}
          title="Toggle Sidebar"
          type="button"
        >
          <Terminal className="mr-3 shrink-0 text-red-500" />
          {!isCollapsed && (
            <div className="overflow-hidden whitespace-nowrap">
              <div className="font-bold font-display text-lg text-white tracking-widest">ADMIN</div>
              <div className="font-mono text-[9px] text-red-500 uppercase">Root Access</div>
            </div>
          )}
        </button>

        <div className="mt-16 flex-1 space-y-1 px-3 py-6 md:mt-0">
          <AdminNavItem
            active={currentView === "dashboard"}
            collapsed={isCollapsed}
            icon={<LayoutDashboard size={18} />}
            label="Главная"
            onClick={() => {
              onViewChange("dashboard");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "catalog"}
            collapsed={isCollapsed}
            icon={<Package size={18} />}
            label="Каталог"
            onClick={() => {
              onViewChange("catalog");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "sales"}
            collapsed={isCollapsed}
            icon={<BarChart3 size={18} />}
            label="Заказы"
            onClick={() => {
              onViewChange("sales");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "users"}
            collapsed={isCollapsed}
            icon={<Users size={18} />}
            label="Пользователи"
            onClick={() => {
              onViewChange("users");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "partners"}
            collapsed={isCollapsed}
            icon={<Crown size={18} />}
            label="VIP Партнёры"
            onClick={() => {
              onViewChange("partners");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "support"}
            collapsed={isCollapsed}
            icon={<LifeBuoy size={18} />}
            label="Поддержка"
            onClick={() => {
              onViewChange("support");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "promo"}
            collapsed={isCollapsed}
            icon={<Tag size={18} />}
            label="Промокоды"
            onClick={() => {
              onViewChange("promo");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "accounting"}
            collapsed={isCollapsed}
            icon={<Calculator size={18} />}
            label="Бухгалтерия"
            onClick={() => {
              onViewChange("accounting");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "withdrawals"}
            collapsed={isCollapsed}
            icon={<Wallet size={18} />}
            label="Выводы"
            onClick={() => {
              onViewChange("withdrawals");
              onClose();
            }}
          />
          <AdminNavItem
            active={currentView === "migration"}
            collapsed={isCollapsed}
            icon={<ArrowRightLeft size={18} />}
            label="Миграция"
            onClick={() => {
              onViewChange("migration");
              onClose();
            }}
          />
        </div>

        <div className="border-white/10 border-t p-4">
          <button
            className={`flex w-full items-center gap-3 rounded-sm p-2 text-gray-500 transition-colors hover:bg-white/5 hover:text-white ${
              isCollapsed ? "justify-center" : ""
            }`}
            onClick={onExit}
            type="button"
          >
            <LogOut size={18} />
            {!isCollapsed && <span className="font-bold text-sm uppercase">Exit System</span>}
          </button>
        </div>
      </div>
    </>
  );
};

export default memo(AdminSidebar);
