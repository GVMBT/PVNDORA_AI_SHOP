/**
 * AdminHeader Component
 *
 * Header for admin panel main content area.
 */

import { Settings } from "lucide-react";
import type React from "react";
import { memo } from "react";
import type { AdminView } from "./types";

interface AdminHeaderProps {
  currentView: AdminView;
}

const VIEW_LABELS: Record<AdminView, string> = {
  dashboard: "Главная",
  catalog: "Каталог",
  sales: "Заказы",
  users: "Пользователи",
  partners: "VIP Партнёры",
  support: "Поддержка",
  promo: "Промокоды",
  migration: "Миграция",
  accounting: "Бухгалтерия",
  withdrawals: "Выводы",
};

const AdminHeader: React.FC<AdminHeaderProps> = ({ currentView }) => {
  return (
    <div className="sticky top-0 z-30 hidden h-20 items-center justify-between border-white/10 border-b bg-[#050505] px-8 md:flex">
      <div>
        <h2 className="font-bold font-display text-2xl text-white uppercase">
          {VIEW_LABELS[currentView] || currentView}
        </h2>
        <div className="font-mono text-[10px] text-gray-500">
          LAST_LOGIN: 2025.10.02 {/* 14:00 */}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="font-bold text-white text-xs">AdminUser_01</div>
          <div className="font-mono text-[10px] text-green-500">ONLINE</div>
        </div>
        <div className="flex h-10 w-10 items-center justify-center rounded-sm border border-red-500/50 bg-red-900/20 text-red-500">
          <Settings size={20} />
        </div>
      </div>
    </div>
  );
};

export default memo(AdminHeader);
