/**
 * AdminUsers Component
 *
 * Управление пользователями - отображение и действия.
 */

import { AnimatePresence, motion } from "framer-motion";
import { Ban, Check, Crown, DollarSign, ExternalLink, Search, X } from "lucide-react";
import type React from "react";
import { memo, useMemo, useState } from "react";
import { API } from "../../config";
import { apiRequest } from "../../utils/apiClient";
import { logger } from "../../utils/logger";
import type { UserData } from "./types";

interface AdminUsersProps {
  users: UserData[];
  onBanUser?: (userId: number, ban: boolean) => void;
  onUpdateBalance?: (userId: number, amount: number) => void;
  onRefresh?: () => void;
}

const AdminUsers: React.FC<AdminUsersProps> = ({ users, onBanUser, onRefresh }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<"ALL" | "USER" | "VIP" | "ADMIN">("ALL");
  const [selectedUser, setSelectedUser] = useState<UserData | null>(null);
  const [processing, setProcessing] = useState(false);
  const [balanceModal, setBalanceModal] = useState<UserData | null>(null);
  const [balanceAmount, setBalanceAmount] = useState("");

  // Filter users
  const filteredUsers = useMemo(() => {
    let result = users;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (u) => u.username.toLowerCase().includes(query) || u.id.toString().includes(query)
      );
    }

    if (roleFilter !== "ALL") {
      result = result.filter((u) => u.role === roleFilter);
    }

    return result;
  }, [users, searchQuery, roleFilter]);

  // Format currency with user's balance currency
  const formatCurrency = (amount: number, currency: string = "USD") => {
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "ADMIN":
        return (
          <span className="text-[10px] px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30">
            ADMIN
          </span>
        );
      case "VIP":
        return (
          <span className="text-[10px] px-2 py-0.5 bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
            VIP
          </span>
        );
      default:
        return (
          <span className="text-[10px] px-2 py-0.5 bg-white/5 text-gray-400 border border-white/10">
            USER
          </span>
        );
    }
  };

  // Toggle VIP status (simple on/off, VIP always gets full access with ARCHITECT status)
  const handleToggleVIP = async () => {
    if (!selectedUser) return;
    setProcessing(true);

    const isCurrentlyVIP = selectedUser.role === "VIP";

    try {
      await apiRequest(`${API.ADMIN_URL}/users/${selectedUser.dbId}/vip`, {
        method: "POST",
        body: JSON.stringify({
          is_partner: !isCurrentlyVIP,
          // VIP always gets full access (level 3) - no partial levels
          partner_level_override: isCurrentlyVIP ? null : 3,
        }),
      });

      setSelectedUser(null);
      if (onRefresh) onRefresh();
    } catch (err) {
      logger.error("Failed to toggle VIP status", err);
      alert("Ошибка при изменении VIP статуса");
    } finally {
      setProcessing(false);
    }
  };

  // Update balance
  const handleUpdateBalance = async () => {
    if (!balanceModal || !balanceAmount) return;
    const amount = Number.parseFloat(balanceAmount);
    if (Number.isNaN(amount)) return;

    setProcessing(true);
    try {
      await apiRequest(`${API.ADMIN_URL}/users/${balanceModal.dbId}/balance`, {
        method: "POST",
        body: JSON.stringify({ amount }),
      });

      setBalanceModal(null);
      setBalanceAmount("");
      if (onRefresh) onRefresh();
    } catch (err) {
      logger.error("Failed to update balance", err);
      alert("Ошибка при обновлении баланса");
    } finally {
      setProcessing(false);
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
            placeholder="Поиск по имени или ID..."
            className="w-full bg-black border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none"
          />
        </div>
        <div className="flex gap-2">
          {(["ALL", "USER", "VIP", "ADMIN"] as const).map((role) => (
            <button
              type="button"
              key={role}
              onClick={() => setRoleFilter(role)}
              className={`px-3 py-2 text-[10px] font-bold uppercase border transition-colors ${
                roleFilter === role
                  ? "bg-pandora-cyan text-black border-pandora-cyan"
                  : "bg-transparent text-gray-400 border-white/20 hover:border-white/40"
              }`}
            >
              {role === "ALL" ? "Все" : role}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Всего</div>
          <div className="text-2xl font-bold text-white">{users.length}</div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">VIP</div>
          <div className="text-2xl font-bold text-yellow-400">
            {users.filter((u) => u.role === "VIP").length}
          </div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Заблокировано</div>
          <div className="text-2xl font-bold text-red-400">
            {users.filter((u) => u.isBanned).length}
          </div>
        </div>
        <div className="bg-[#0e0e0e] border border-white/10 p-4">
          <div className="text-[10px] text-gray-500 uppercase mb-1">Активных сегодня</div>
          <div className="text-2xl font-bold text-green-400">—</div>
        </div>
      </div>

      {/* Users Table - Desktop */}
      <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-white/5 text-gray-400 uppercase">
            <tr>
              <th className="p-4">Пользователь</th>
              <th className="p-4">Роль</th>
              <th className="p-4">Баланс</th>
              <th className="p-4">Заказы</th>
              <th className="p-4">Потрачено</th>
              <th className="p-4">Статус</th>
              <th className="p-4 text-right">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-gray-500">
                  Пользователи не найдены
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
                <tr
                  key={u.id}
                  className={`hover:bg-white/5 transition-colors ${u.isBanned ? "opacity-50" : ""}`}
                >
                  <td className="p-4">
                    <a
                      href={`https://t.me/${u.username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-bold text-white hover:text-pandora-cyan transition-colors inline-flex items-center gap-1"
                    >
                      @{u.username}
                      <ExternalLink size={10} className="opacity-50" />
                    </a>
                    <div className="text-[10px] text-gray-600">ID: {u.id}</div>
                  </td>
                  <td className="p-4">{getRoleBadge(u.role)}</td>
                  <td className="p-4 text-pandora-cyan">
                    {formatCurrency(u.balance, u.balanceCurrency)}
                  </td>
                  <td className="p-4">{u.purchases}</td>
                  <td className="p-4">{formatCurrency(u.spent, "USD")}</td>
                  <td className="p-4">
                    {u.isBanned ? (
                      <span className="text-[10px] px-2 py-0.5 bg-red-500/20 text-red-400 border border-red-500/30">
                        BLOCKED
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
                        type="button"
                        onClick={() => setBalanceModal(u)}
                        className="p-1.5 border border-white/10 hover:border-pandora-cyan hover:text-pandora-cyan transition-colors"
                        title="Изменить баланс"
                      >
                        <DollarSign size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => setSelectedUser(u)}
                        className={`p-1.5 border transition-colors ${
                          u.role === "VIP"
                            ? "border-yellow-500/30 text-yellow-400 hover:border-yellow-500"
                            : "border-white/10 text-gray-400 hover:border-yellow-500 hover:text-yellow-400"
                        }`}
                        title={u.role === "VIP" ? "Отозвать VIP" : "Назначить VIP"}
                      >
                        <Crown size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => onBanUser?.(u.id, !u.isBanned)}
                        className={`p-1.5 border transition-colors ${
                          u.isBanned
                            ? "border-green-500/30 text-green-400 hover:border-green-500"
                            : "border-red-500/30 text-red-400 hover:border-red-500"
                        }`}
                        title={u.isBanned ? "Разблокировать" : "Заблокировать"}
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
            Пользователи не найдены
          </div>
        ) : (
          filteredUsers.map((u) => (
            <div
              key={u.id}
              className={`bg-[#0e0e0e] border border-white/10 p-4 ${u.isBanned ? "opacity-50" : ""}`}
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
                      BLOCKED
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center mb-3">
                <div>
                  <div className="text-[10px] text-gray-500">Баланс</div>
                  <div className="text-sm font-bold text-pandora-cyan">
                    {formatCurrency(u.balance, u.balanceCurrency)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500">Заказы</div>
                  <div className="text-sm font-bold text-white">{u.purchases}</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500">Потрачено</div>
                  <div className="text-sm font-bold text-white">
                    {formatCurrency(u.spent, "USD")}
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setBalanceModal(u)}
                  className="flex-1 flex items-center justify-center gap-2 py-2 text-[10px] bg-white/5 hover:bg-pandora-cyan hover:text-black transition-colors uppercase font-bold"
                >
                  <DollarSign size={12} /> Баланс
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedUser(u)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-[10px] uppercase font-bold ${
                    u.role === "VIP"
                      ? "bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500 hover:text-black"
                      : "bg-white/5 hover:bg-yellow-500 hover:text-black"
                  } transition-colors`}
                >
                  <Crown size={12} /> VIP
                </button>
                <button
                  type="button"
                  onClick={() => onBanUser?.(u.id, !u.isBanned)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-[10px] uppercase font-bold transition-colors ${
                    u.isBanned
                      ? "bg-green-500/20 text-green-400 hover:bg-green-500 hover:text-black"
                      : "bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-black"
                  }`}
                >
                  <Ban size={12} /> {u.isBanned ? "Разбан" : "Бан"}
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* VIP Modal - Simplified toggle */}
      <AnimatePresence>
        {selectedUser && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <button
              type="button"
              className="absolute inset-0 bg-black/80 backdrop-blur-sm cursor-default"
              onClick={() => !processing && setSelectedUser(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !processing) setSelectedUser(null);
              }}
              aria-label="Close modal"
            />
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-sm bg-[#080808] border border-white/20 p-6 shadow-2xl"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <Crown size={18} className="text-yellow-500" />
                    VIP Статус
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">@{selectedUser.username}</p>
                </div>
                <button
                  type="button"
                  onClick={() => !processing && setSelectedUser(null)}
                  className="text-gray-500 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Current Status */}
              <div className="bg-white/5 p-4 border border-white/10 mb-6">
                <div className="text-[10px] text-gray-500 uppercase mb-2">Текущий статус</div>
                <div className="flex items-center gap-3">
                  {getRoleBadge(selectedUser.role)}
                  {selectedUser.role === "VIP" && (
                    <span className="text-xs text-yellow-400">ARCHITECT • Полный доступ</span>
                  )}
                </div>
              </div>

              {/* Info about VIP */}
              <div className="text-xs text-gray-500 mb-6 p-3 bg-black/50 border border-white/10">
                {selectedUser.role === "VIP" ? (
                  <>
                    <p className="mb-2">VIP пользователь имеет:</p>
                    <ul className="list-disc list-inside space-y-1 text-gray-400">
                      <li>Статус ARCHITECT</li>
                      <li>Все реферальные уровни открыты</li>
                      <li>Максимальные комиссии</li>
                    </ul>
                  </>
                ) : (
                  <p>
                    VIP статус даёт пользователю ARCHITECT ранг, открытые реферальные уровни и
                    максимальные комиссии.
                  </p>
                )}
              </div>

              {/* Toggle Button */}
              <button
                type="button"
                onClick={handleToggleVIP}
                disabled={processing}
                className={`w-full py-3 font-bold text-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2 ${
                  selectedUser.role === "VIP"
                    ? "bg-red-500 text-white hover:bg-red-400"
                    : "bg-yellow-500 text-black hover:bg-yellow-400"
                }`}
              >
                {selectedUser.role === "VIP" ? (
                  <>
                    <X size={16} />
                    Отозвать VIP статус
                  </>
                ) : (
                  <>
                    <Crown size={16} />
                    Назначить VIP статус
                  </>
                )}
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Balance Modal */}
      <AnimatePresence>
        {balanceModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <button
              type="button"
              className="absolute inset-0 bg-black/80 backdrop-blur-sm cursor-default"
              onClick={() => !processing && setBalanceModal(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !processing) setBalanceModal(null);
              }}
              aria-label="Close modal"
            />
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-sm bg-[#080808] border border-white/20 p-6 shadow-2xl"
            >
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <DollarSign size={18} className="text-pandora-cyan" />
                    Изменить баланс
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">@{balanceModal.username}</p>
                </div>
                <button
                  type="button"
                  onClick={() => !processing && setBalanceModal(null)}
                  className="text-gray-500 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Current Balance */}
              <div className="bg-white/5 p-3 border border-white/10 mb-4">
                <div className="text-[10px] text-gray-500 uppercase mb-1">Текущий баланс</div>
                <div className="text-xl font-bold text-pandora-cyan">
                  {formatCurrency(balanceModal.balance, balanceModal.balanceCurrency)}
                </div>
              </div>

              {/* Amount Input */}
              <div className="mb-4">
                <label
                  htmlFor="balance-amount"
                  className="text-[10px] text-gray-500 uppercase mb-1 block"
                >
                  Сумма (+ или -)
                </label>
                <input
                  id="balance-amount"
                  type="number"
                  value={balanceAmount}
                  onChange={(e) => setBalanceAmount(e.target.value)}
                  placeholder="10.00 или -5.00"
                  step="0.01"
                  className="w-full bg-black border border-white/20 p-2.5 text-white text-sm focus:border-pandora-cyan outline-none"
                />
                <p className="text-[9px] text-gray-600 mt-1">
                  Положительное число для пополнения, отрицательное для списания
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleUpdateBalance}
                  disabled={processing || !balanceAmount}
                  className="flex-1 py-2.5 bg-pandora-cyan text-black font-bold text-sm hover:bg-white transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <Check size={16} />
                  Применить
                </button>
                <button
                  type="button"
                  onClick={() => setBalanceModal(null)}
                  disabled={processing}
                  className="flex-1 py-2.5 bg-white/10 text-white font-bold text-sm hover:bg-white/20 transition-colors flex items-center justify-center gap-2"
                >
                  <X size={16} />
                  Отмена
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default memo(AdminUsers);
