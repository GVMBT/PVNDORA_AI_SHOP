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

  // Format currency (all amounts are in RUB after migration)
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: "RUB",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const getRoleBadge = (role: string) => {
    switch (role) {
      case "ADMIN":
        return (
          <span className="border border-red-500/30 bg-red-500/20 px-2 py-0.5 text-[10px] text-red-400">
            ADMIN
          </span>
        );
      case "VIP":
        return (
          <span className="border border-yellow-500/30 bg-yellow-500/20 px-2 py-0.5 text-[10px] text-yellow-400">
            VIP
          </span>
        );
      default:
        return (
          <span className="border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-gray-400">
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
    if (!(balanceModal && balanceAmount)) return;
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
      <div className="flex flex-col gap-4 rounded-sm border border-white/10 bg-[#0e0e0e] p-4 md:flex-row">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3 -translate-y-1/2 text-gray-500" size={14} />
          <input
            className="w-full border border-white/20 bg-black py-2 pr-4 pl-9 font-mono text-white text-xs outline-none focus:border-pandora-cyan"
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Поиск по имени или ID..."
            type="text"
            value={searchQuery}
          />
        </div>
        <div className="flex gap-2">
          {(["ALL", "USER", "VIP", "ADMIN"] as const).map((role) => (
            <button
              className={`border px-3 py-2 font-bold text-[10px] uppercase transition-colors ${
                roleFilter === role
                  ? "border-pandora-cyan bg-pandora-cyan text-black"
                  : "border-white/20 bg-transparent text-gray-400 hover:border-white/40"
              }`}
              key={role}
              onClick={() => setRoleFilter(role)}
              type="button"
            >
              {role === "ALL" ? "Все" : role}
            </button>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="border border-white/10 bg-[#0e0e0e] p-4">
          <div className="mb-1 text-[10px] text-gray-500 uppercase">Всего</div>
          <div className="font-bold text-2xl text-white">{users.length}</div>
        </div>
        <div className="border border-white/10 bg-[#0e0e0e] p-4">
          <div className="mb-1 text-[10px] text-gray-500 uppercase">VIP</div>
          <div className="font-bold text-2xl text-yellow-400">
            {users.filter((u) => u.role === "VIP").length}
          </div>
        </div>
        <div className="border border-white/10 bg-[#0e0e0e] p-4">
          <div className="mb-1 text-[10px] text-gray-500 uppercase">Заблокировано</div>
          <div className="font-bold text-2xl text-red-400">
            {users.filter((u) => u.isBanned).length}
          </div>
        </div>
        <div className="border border-white/10 bg-[#0e0e0e] p-4">
          <div className="mb-1 text-[10px] text-gray-500 uppercase">Активных сегодня</div>
          <div className="font-bold text-2xl text-green-400">—</div>
        </div>
      </div>

      {/* Users Table - Desktop */}
      <div className="hidden overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e] md:block">
        <table className="w-full text-left font-mono text-xs">
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
                <td className="p-8 text-center text-gray-500" colSpan={7}>
                  Пользователи не найдены
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
                <tr
                  className={`transition-colors hover:bg-white/5 ${u.isBanned ? "opacity-50" : ""}`}
                  key={u.id}
                >
                  <td className="p-4">
                    <a
                      className="inline-flex items-center gap-1 font-bold text-white transition-colors hover:text-pandora-cyan"
                      href={`https://t.me/${u.username}`}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      @{u.username}
                      <ExternalLink className="opacity-50" size={10} />
                    </a>
                    <div className="text-[10px] text-gray-600">ID: {u.id}</div>
                  </td>
                  <td className="p-4">{getRoleBadge(u.role)}</td>
                  <td className="p-4 text-pandora-cyan">{formatCurrency(u.balance)}</td>
                  <td className="p-4">{u.purchases}</td>
                  <td className="p-4">{formatCurrency(u.spent)}</td>
                  <td className="p-4">
                    {u.isBanned ? (
                      <span className="border border-red-500/30 bg-red-500/20 px-2 py-0.5 text-[10px] text-red-400">
                        BLOCKED
                      </span>
                    ) : (
                      <span className="border border-green-500/30 bg-green-500/20 px-2 py-0.5 text-[10px] text-green-400">
                        ACTIVE
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        className="border border-white/10 p-1.5 transition-colors hover:border-pandora-cyan hover:text-pandora-cyan"
                        onClick={() => setBalanceModal(u)}
                        title="Изменить баланс"
                        type="button"
                      >
                        <DollarSign size={14} />
                      </button>
                      <button
                        className={`border p-1.5 transition-colors ${
                          u.role === "VIP"
                            ? "border-yellow-500/30 text-yellow-400 hover:border-yellow-500"
                            : "border-white/10 text-gray-400 hover:border-yellow-500 hover:text-yellow-400"
                        }`}
                        onClick={() => setSelectedUser(u)}
                        title={u.role === "VIP" ? "Отозвать VIP" : "Назначить VIP"}
                        type="button"
                      >
                        <Crown size={14} />
                      </button>
                      <button
                        className={`border p-1.5 transition-colors ${
                          u.isBanned
                            ? "border-green-500/30 text-green-400 hover:border-green-500"
                            : "border-red-500/30 text-red-400 hover:border-red-500"
                        }`}
                        onClick={() => onBanUser?.(u.id, !u.isBanned)}
                        title={u.isBanned ? "Разблокировать" : "Заблокировать"}
                        type="button"
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
      <div className="space-y-4 md:hidden">
        {filteredUsers.length === 0 ? (
          <div className="border border-white/10 bg-[#0e0e0e] p-8 text-center text-gray-500">
            Пользователи не найдены
          </div>
        ) : (
          filteredUsers.map((u) => (
            <div
              className={`border border-white/10 bg-[#0e0e0e] p-4 ${u.isBanned ? "opacity-50" : ""}`}
              key={u.id}
            >
              <div className="mb-3 flex items-start justify-between">
                <div>
                  <a
                    className="font-bold text-white transition-colors hover:text-pandora-cyan"
                    href={`https://t.me/${u.username}`}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    @{u.username}
                  </a>
                  <div className="text-[10px] text-gray-600">ID: {u.id}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {getRoleBadge(u.role)}
                  {u.isBanned && (
                    <span className="border border-red-500/30 bg-red-500/20 px-2 py-0.5 text-[10px] text-red-400">
                      BLOCKED
                    </span>
                  )}
                </div>
              </div>

              <div className="mb-3 grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-[10px] text-gray-500">Баланс</div>
                  <div className="font-bold text-pandora-cyan text-sm">
                    {formatCurrency(u.balance)}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500">Заказы</div>
                  <div className="font-bold text-sm text-white">{u.purchases}</div>
                </div>
                <div>
                  <div className="text-[10px] text-gray-500">Потрачено</div>
                  <div className="font-bold text-sm text-white">{formatCurrency(u.spent)}</div>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  className="flex flex-1 items-center justify-center gap-2 bg-white/5 py-2 font-bold text-[10px] uppercase transition-colors hover:bg-pandora-cyan hover:text-black"
                  onClick={() => setBalanceModal(u)}
                  type="button"
                >
                  <DollarSign size={12} /> Баланс
                </button>
                <button
                  className={`flex flex-1 items-center justify-center gap-2 py-2 font-bold text-[10px] uppercase ${
                    u.role === "VIP"
                      ? "bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500 hover:text-black"
                      : "bg-white/5 hover:bg-yellow-500 hover:text-black"
                  } transition-colors`}
                  onClick={() => setSelectedUser(u)}
                  type="button"
                >
                  <Crown size={12} /> VIP
                </button>
                <button
                  className={`flex flex-1 items-center justify-center gap-2 py-2 font-bold text-[10px] uppercase transition-colors ${
                    u.isBanned
                      ? "bg-green-500/20 text-green-400 hover:bg-green-500 hover:text-black"
                      : "bg-red-500/20 text-red-400 hover:bg-red-500 hover:text-black"
                  }`}
                  onClick={() => onBanUser?.(u.id, !u.isBanned)}
                  type="button"
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
              aria-label="Close modal"
              className="absolute inset-0 cursor-default bg-black/80 backdrop-blur-sm"
              onClick={() => !processing && setSelectedUser(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !processing) setSelectedUser(null);
              }}
              type="button"
            />
            <motion.div
              animate={{ scale: 1, opacity: 1 }}
              className="relative w-full max-w-sm border border-white/20 bg-[#080808] p-6 shadow-2xl"
              exit={{ scale: 0.9, opacity: 0 }}
              initial={{ scale: 0.9, opacity: 0 }}
            >
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h3 className="flex items-center gap-2 font-bold text-lg text-white">
                    <Crown className="text-yellow-500" size={18} />
                    VIP Статус
                  </h3>
                  <p className="mt-1 text-gray-500 text-xs">@{selectedUser.username}</p>
                </div>
                <button
                  className="text-gray-500 hover:text-white"
                  onClick={() => !processing && setSelectedUser(null)}
                  type="button"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Current Status */}
              <div className="mb-6 border border-white/10 bg-white/5 p-4">
                <div className="mb-2 text-[10px] text-gray-500 uppercase">Текущий статус</div>
                <div className="flex items-center gap-3">
                  {getRoleBadge(selectedUser.role)}
                  {selectedUser.role === "VIP" && (
                    <span className="text-xs text-yellow-400">ARCHITECT • Полный доступ</span>
                  )}
                </div>
              </div>

              {/* Info about VIP */}
              <div className="mb-6 border border-white/10 bg-black/50 p-3 text-gray-500 text-xs">
                {selectedUser.role === "VIP" ? (
                  <>
                    <p className="mb-2">VIP пользователь имеет:</p>
                    <ul className="list-inside list-disc space-y-1 text-gray-400">
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
                className={`flex w-full items-center justify-center gap-2 py-3 font-bold text-sm transition-colors disabled:opacity-50 ${
                  selectedUser.role === "VIP"
                    ? "bg-red-500 text-white hover:bg-red-400"
                    : "bg-yellow-500 text-black hover:bg-yellow-400"
                }`}
                disabled={processing}
                onClick={handleToggleVIP}
                type="button"
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
              aria-label="Close modal"
              className="absolute inset-0 cursor-default bg-black/80 backdrop-blur-sm"
              onClick={() => !processing && setBalanceModal(null)}
              onKeyDown={(e) => {
                if (e.key === "Escape" && !processing) setBalanceModal(null);
              }}
              type="button"
            />
            <motion.div
              animate={{ scale: 1, opacity: 1 }}
              className="relative w-full max-w-sm border border-white/20 bg-[#080808] p-6 shadow-2xl"
              exit={{ scale: 0.9, opacity: 0 }}
              initial={{ scale: 0.9, opacity: 0 }}
            >
              <div className="mb-6 flex items-start justify-between">
                <div>
                  <h3 className="flex items-center gap-2 font-bold text-lg text-white">
                    <DollarSign className="text-pandora-cyan" size={18} />
                    Изменить баланс
                  </h3>
                  <p className="mt-1 text-gray-500 text-xs">@{balanceModal.username}</p>
                </div>
                <button
                  className="text-gray-500 hover:text-white"
                  onClick={() => !processing && setBalanceModal(null)}
                  type="button"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Current Balance */}
              <div className="mb-4 border border-white/10 bg-white/5 p-3">
                <div className="mb-1 text-[10px] text-gray-500 uppercase">Текущий баланс</div>
                <div className="font-bold text-pandora-cyan text-xl">
                  {formatCurrency(balanceModal.balance)}
                </div>
              </div>

              {/* Amount Input */}
              <div className="mb-4">
                <label
                  className="mb-1 block text-[10px] text-gray-500 uppercase"
                  htmlFor="balance-amount"
                >
                  Сумма (+ или -)
                </label>
                <input
                  className="w-full border border-white/20 bg-black p-2.5 text-sm text-white outline-none focus:border-pandora-cyan"
                  id="balance-amount"
                  onChange={(e) => setBalanceAmount(e.target.value)}
                  placeholder="10.00 или -5.00"
                  step="0.01"
                  type="number"
                  value={balanceAmount}
                />
                <p className="mt-1 text-[9px] text-gray-600">
                  Положительное число для пополнения, отрицательное для списания
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  className="flex flex-1 items-center justify-center gap-2 bg-pandora-cyan py-2.5 font-bold text-black text-sm transition-colors hover:bg-white disabled:opacity-50"
                  disabled={processing || !balanceAmount}
                  onClick={handleUpdateBalance}
                  type="button"
                >
                  <Check size={16} />
                  Применить
                </button>
                <button
                  className="flex flex-1 items-center justify-center gap-2 bg-white/10 py-2.5 font-bold text-sm text-white transition-colors hover:bg-white/20"
                  disabled={processing}
                  onClick={() => setBalanceModal(null)}
                  type="button"
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
