/**
 * AdminWithdrawals Component
 *
 * Управление заявками на вывод средств.
 */

import { ArrowUpRight, Check, ExternalLink, Send, Wallet, X } from "lucide-react";
import type React from "react";
import { memo, useCallback, useState } from "react";
import { useAdmin } from "../../hooks/useAdmin";
import { logger } from "../../utils/logger";
import type { WithdrawalData } from "./types";

interface AdminWithdrawalsProps {
  withdrawals: WithdrawalData[];
  onRefresh?: () => void;
}

const AdminWithdrawals: React.FC<AdminWithdrawalsProps> = ({ withdrawals, onRefresh }) => {
  const [selectedWithdrawalId, setSelectedWithdrawalId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [processing, setProcessing] = useState(false);
  const { approveWithdrawal, rejectWithdrawal, completeWithdrawal } = useAdmin();

  const selectedWithdrawal = withdrawals.find((w) => w.id === selectedWithdrawalId);

  const handleApprove = useCallback(async () => {
    if (!selectedWithdrawalId) return;

    setProcessing(true);
    try {
      await approveWithdrawal(selectedWithdrawalId, comment.trim() || undefined);
      setComment("");
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      logger.error("Failed to approve withdrawal", err);
    } finally {
      setProcessing(false);
    }
  }, [selectedWithdrawalId, comment, approveWithdrawal, onRefresh]);

  const handleReject = useCallback(async () => {
    if (!selectedWithdrawalId) return;

    setProcessing(true);
    try {
      await rejectWithdrawal(selectedWithdrawalId, comment.trim() || undefined);
      setComment("");
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      logger.error("Failed to reject withdrawal", err);
    } finally {
      setProcessing(false);
    }
  }, [selectedWithdrawalId, comment, rejectWithdrawal, onRefresh]);

  const handleComplete = useCallback(async () => {
    if (!selectedWithdrawalId) return;

    setProcessing(true);
    try {
      await completeWithdrawal(selectedWithdrawalId, comment.trim() || undefined);
      setComment("");
      if (onRefresh) {
        onRefresh();
      }
    } catch (err) {
      logger.error("Failed to complete withdrawal", err);
    } finally {
      setProcessing(false);
    }
  }, [selectedWithdrawalId, comment, completeWithdrawal, onRefresh]);

  const getStatusColor = (status: string) => {
    switch (status?.toUpperCase()) {
      case "PENDING":
        return "text-yellow-400";
      case "PROCESSING":
        return "text-blue-400";
      case "COMPLETED":
        return "text-green-400";
      case "REJECTED":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status?.toUpperCase()) {
      case "PENDING":
        return "ОЖИДАЕТ";
      case "PROCESSING":
        return "В ОБРАБОТКЕ";
      case "COMPLETED":
        return "ВЫПОЛНЕНО";
      case "REJECTED":
        return "ОТКЛОНЕНО";
      default:
        return status?.toUpperCase() || "ОЖИДАЕТ";
    }
  };

  // Helper function to render action buttons based on withdrawal status
  const renderActionButtons = () => {
    if (!selectedWithdrawal) return null;

    const status = selectedWithdrawal.status?.toUpperCase();

    if (status === "PENDING") {
      return (
        <div className="p-4 border-t border-white/10 space-y-3">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий (опционально)..."
            className="w-full bg-black border border-white/20 p-3 text-xs text-white outline-none resize-none"
            rows={3}
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleApprove}
              disabled={processing}
              className="flex-1 flex items-center justify-center gap-2 bg-green-500/20 border border-green-500/50 text-green-400 px-4 py-2 text-[10px] font-bold font-mono hover:bg-green-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Check size={14} />
              ОДОБРИТЬ
            </button>
            <button
              type="button"
              onClick={handleReject}
              disabled={processing}
              className="flex-1 flex items-center justify-center gap-2 bg-red-500/20 border border-red-500/50 text-red-400 px-4 py-2 text-[10px] font-bold font-mono hover:bg-red-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <X size={14} />
              ОТКЛОНИТЬ
            </button>
          </div>
        </div>
      );
    }

    if (status === "PROCESSING") {
      return (
        <div className="p-4 border-t border-white/10 space-y-3">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий при завершении (опционально)..."
            className="w-full bg-black border border-white/20 p-3 text-xs text-white outline-none resize-none"
            rows={3}
          />
          <button
            type="button"
            onClick={handleComplete}
            disabled={processing}
            className="w-full flex items-center justify-center gap-2 bg-blue-500/20 border border-blue-500/50 text-blue-400 px-4 py-2 text-[10px] font-bold font-mono hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send size={14} />
            ОТМЕТИТЬ ВЫПОЛНЕННЫМ
          </button>
        </div>
      );
    }

    return (
      <div className="p-4 border-t border-white/10">
        <div className="text-center text-gray-600 text-xs">
          Заявка {getStatusLabel(selectedWithdrawal.status).toLowerCase()}
        </div>
      </div>
    );
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Н/Д";
    try {
      return new Date(dateStr).toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const formatAmount = (amount: number, showCurrency = true) => {
    // All amounts in admin panel are in USD (base currency)
    return showCurrency ? `$${amount.toFixed(2)} USD` : `$${amount.toFixed(2)}`;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
      {/* Withdrawal List */}
      <div
        className={`${
          selectedWithdrawalId ? "hidden lg:block" : "block"
        } lg:col-span-1 space-y-4 overflow-y-auto pr-2`}
      >
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-display font-bold text-white">ОЧЕРЕДЬ</h3>
          <div className="text-xs font-mono text-gray-500">
            {withdrawals.filter((w) => w.status?.toUpperCase() === "PENDING").length} ожидает
          </div>
        </div>
        {withdrawals.length === 0 ? (
          <div className="bg-[#0e0e0e] border border-white/10 p-8 text-center text-gray-500 text-xs">
            Нет заявок на вывод
          </div>
        ) : (
          withdrawals.map((w) => (
            <button
              key={w.id}
              type="button"
              onClick={() => setSelectedWithdrawalId(w.id)}
              className={`bg-[#0e0e0e] border p-4 transition-colors cursor-pointer group relative text-left w-full ${
                selectedWithdrawalId === w.id
                  ? "border-pandora-cyan bg-pandora-cyan/5"
                  : "border-white/10 hover:border-white/30"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <span className="text-[10px] font-mono text-gray-500">{w.id.slice(0, 8)}</span>
                <span className={`text-[10px] font-mono ${getStatusColor(w.status)}`}>
                  {getStatusLabel(w.status)}
                </span>
              </div>
              <div className="font-bold text-white text-sm mb-1">{formatAmount(w.amount)}</div>
              <div className="text-xs text-gray-400 mb-1">
                {w.first_name || w.username || `Пользователь ${w.telegram_id || "Неизвестно"}`}
              </div>
              <div className="text-[10px] font-mono text-gray-600 mt-1">
                {formatDate(w.created_at)}
              </div>
            </button>
          ))
        )}
      </div>

      {/* Detail Area */}
      <div
        className={`${
          selectedWithdrawalId ? "flex" : "hidden lg:flex"
        } lg:col-span-2 bg-[#0e0e0e] border border-white/10 flex-col h-full relative`}
      >
        {selectedWithdrawal ? (
          <>
            <div className="p-4 border-b border-white/10 bg-black/50">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setSelectedWithdrawalId(null)}
                    className="lg:hidden text-gray-500 hover:text-white"
                  >
                    <ArrowUpRight className="rotate-[-135deg]" size={20} />
                  </button>
                  <div>
                    <h3 className="font-bold text-white">
                      ВЫВОД-{selectedWithdrawal.id.slice(0, 8)}
                    </h3>
                    <div className="text-[10px] font-mono text-gray-500 mt-1">
                      {formatDate(selectedWithdrawal.created_at)}
                    </div>
                  </div>
                </div>
                <div
                  className={`text-[10px] font-mono px-2 py-1 border ${getStatusColor(selectedWithdrawal.status)} border-current/30`}
                >
                  {getStatusLabel(selectedWithdrawal.status)}
                </div>
              </div>

              {/* Withdrawal Info */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="text-gray-500 mb-1">Сумма</div>
                  <div className="text-white font-mono text-lg font-bold">
                    {formatAmount(selectedWithdrawal.amount)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Метод</div>
                  <div className="text-white font-mono uppercase">
                    {selectedWithdrawal.payment_method || "КРИПТО"}
                  </div>
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Пользователь</div>
                  <div className="text-white font-mono">
                    {selectedWithdrawal.first_name || selectedWithdrawal.username || "Неизвестно"}
                  </div>
                  {selectedWithdrawal.telegram_id && (
                    <a
                      href={`tg://user?id=${selectedWithdrawal.telegram_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-pandora-cyan hover:text-pandora-cyan/80 mt-1"
                    >
                      <ExternalLink size={12} />
                      <span className="text-[10px]">Написать в Telegram</span>
                    </a>
                  )}
                </div>
                <div>
                  <div className="text-gray-500 mb-1">Баланс</div>
                  <div className="text-white font-mono">
                    {selectedWithdrawal.user_balance !== undefined
                      ? formatAmount(selectedWithdrawal.user_balance)
                      : "Н/Д"}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-1 p-4 overflow-y-auto">
              {/* Payment Details */}
              <div className="mb-6">
                <div className="text-[10px] font-mono text-gray-500 mb-2">РЕКВИЗИТЫ</div>
                <div className="bg-black/50 border border-white/10 p-4">
                  {selectedWithdrawal.payment_details?.details ? (
                    <div className="font-mono text-sm text-white break-all select-all">
                      {selectedWithdrawal.payment_details.details}
                    </div>
                  ) : (
                    <div className="text-xs text-gray-500">Реквизиты не указаны</div>
                  )}
                </div>
              </div>

              {/* Admin Comment (if exists) */}
              {selectedWithdrawal.admin_comment && (
                <div className="mb-6">
                  <div className="text-[10px] font-mono text-gray-500 mb-2">КОММЕНТАРИЙ АДМИНА</div>
                  <div className="bg-pandora-cyan/10 border border-pandora-cyan/30 p-4 text-xs text-gray-300 whitespace-pre-wrap">
                    {selectedWithdrawal.admin_comment}
                  </div>
                </div>
              )}

              {/* Processed Info */}
              {selectedWithdrawal.processed_at && (
                <div className="mb-6">
                  <div className="text-[10px] font-mono text-gray-500 mb-2">ОБРАБОТАНО</div>
                  <div className="text-xs text-gray-400">
                    {formatDate(selectedWithdrawal.processed_at)}
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            {renderActionButtons()}
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 opacity-50">
            <Wallet size={48} className="mb-4" />
            <span className="font-mono text-xs uppercase tracking-widest">Выберите заявку</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(AdminWithdrawals);
