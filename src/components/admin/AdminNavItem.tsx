/**
 * AdminNavItem Component
 *
 * Navigation item for admin sidebar.
 */

import type React from "react";
import { memo } from "react";

interface AdminNavItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
  collapsed: boolean;
}

const AdminNavItem: React.FC<AdminNavItemProps> = ({ icon, label, active, onClick, collapsed }) => (
  <button
    className={`group relative flex w-full items-center gap-3 rounded-sm p-3 transition-all ${
      active ? "bg-white/10 text-white" : "text-gray-500 hover:bg-white/5 hover:text-white"
    } ${collapsed ? "justify-center" : ""}`}
    onClick={onClick}
    type="button"
  >
    {active && <div className="absolute top-0 bottom-0 left-0 w-1 rounded-l-sm bg-red-500" />}
    {icon}
    {!collapsed && <span className="font-bold text-xs uppercase tracking-wide">{label}</span>}
  </button>
);

export default memo(AdminNavItem);
