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
        <div className="space-y-3 border-white/10 border-t p-4">
          <textarea
            className="w-full resize-none border border-white/20 bg-black p-3 text-white text-xs outline-none"
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий (опционально)..."
            rows={3}
            value={comment}
          />
          <div className="flex gap-2">
            <button
              className="flex flex-1 items-center justify-center gap-2 border border-green-500/50 bg-green-500/20 px-4 py-2 font-bold font-mono text-[10px] text-green-400 hover:bg-green-500/30 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={processing}
              onClick={handleApprove}
              type="button"
            >
              <Check size={14} />
              ОДОБРИТЬ
            </button>
            <button
              className="flex flex-1 items-center justify-center gap-2 border border-red-500/50 bg-red-500/20 px-4 py-2 font-bold font-mono text-[10px] text-red-400 hover:bg-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={processing}
              onClick={handleReject}
              type="button"
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
        <div className="space-y-3 border-white/10 border-t p-4">
          <textarea
            className="w-full resize-none border border-white/20 bg-black p-3 text-white text-xs outline-none"
            onChange={(e) => setComment(e.target.value)}
            placeholder="Комментарий при завершении (опционально)..."
            rows={3}
            value={comment}
          />
          <button
            className="flex w-full items-center justify-center gap-2 border border-blue-500/50 bg-blue-500/20 px-4 py-2 font-bold font-mono text-[10px] text-blue-400 hover:bg-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
            disabled={processing}
            onClick={handleComplete}
            type="button"
          >
            <Send size={14} />
            ОТМЕТИТЬ ВЫПОЛНЕННЫМ
          </button>
        </div>
      );
    }

    return (
      <div className="border-white/10 border-t p-4">
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

  const formatAmountWithCurrency = (amount: number, currency?: string | null) => {
    // Use the actual currency from the withdrawal request
    const currencySymbol = currency === "USD" ? "$" : "₽";
    return `${Math.round(amount)} ${currencySymbol}`;
  };

  return (
    <div className="grid h-[calc(100vh-200px)] grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Withdrawal List */}
      <div
        className={`${
          selectedWithdrawalId ? "hidden lg:block" : "block"
        } space-y-4 overflow-y-auto pr-2 lg:col-span-1`}
      >
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-bold font-display text-white">ОЧЕРЕДЬ</h3>
          <div className="font-mono text-gray-500 text-xs">
            {withdrawals.filter((w) => w.status?.toUpperCase() === "PENDING").length} ожидает
          </div>
        </div>
        {withdrawals.length === 0 ? (
          <div className="border border-white/10 bg-[#0e0e0e] p-8 text-center text-gray-500 text-xs">
            Нет заявок на вывод
          </div>
        ) : (
          withdrawals.map((w) => (
            <button
              className={`group relative w-full cursor-pointer border bg-[#0e0e0e] p-4 text-left transition-colors ${
                selectedWithdrawalId === w.id
                  ? "border-pandora-cyan bg-pandora-cyan/5"
                  : "border-white/10 hover:border-white/30"
              }`}
              key={w.id}
              onClick={() => setSelectedWithdrawalId(w.id)}
              type="button"
            >
              <div className="mb-2 flex items-start justify-between">
                <span className="font-mono text-[10px] text-gray-500">{w.id.slice(0, 8)}</span>
                <span className={`font-mono text-[10px] ${getStatusColor(w.status)}`}>
                  {getStatusLabel(w.status)}
                </span>
              </div>
              <div className="mb-1 font-bold text-sm text-white">
                {formatAmountWithCurrency(w.amount_debited ?? w.amount, w.balance_currency)}
              </div>
              <div className="mb-1 text-gray-400 text-xs">
                {w.first_name || w.username || `Пользователь ${w.telegram_id || "Неизвестно"}`}
              </div>
              <div className="mt-1 font-mono text-[10px] text-gray-600">
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
        } relative h-full flex-col border border-white/10 bg-[#0e0e0e] lg:col-span-2`}
      >
        {selectedWithdrawal ? (
          <>
            <div className="border-white/10 border-b bg-black/50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    className="text-gray-500 hover:text-white lg:hidden"
                    onClick={() => setSelectedWithdrawalId(null)}
                    type="button"
                  >
                    <ArrowUpRight className="rotate-[-135deg]" size={20} />
                  </button>
                  <div>
                    <h3 className="font-bold text-white">
                      ВЫВОД-{selectedWithdrawal.id.slice(0, 8)}
                    </h3>
                    <div className="mt-1 font-mono text-[10px] text-gray-500">
                      {formatDate(selectedWithdrawal.created_at)}
                    </div>
                  </div>
                </div>
                <div
                  className={`border px-2 py-1 font-mono text-[10px] ${getStatusColor(selectedWithdrawal.status)} border-current/30`}
                >
                  {getStatusLabel(selectedWithdrawal.status)}
                </div>
              </div>

              {/* Withdrawal Info */}
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <div className="mb-1 text-gray-500">Сумма</div>
                  <div className="font-bold font-mono text-lg text-white">
                    {formatAmountWithCurrency(
                      selectedWithdrawal.amount_debited ?? selectedWithdrawal.amount,
                      selectedWithdrawal.balance_currency
                    )}
                  </div>
                  {selectedWithdrawal.amount_to_pay && (
                    <div className="mt-1 text-gray-400 text-xs">
                      К выплате: {selectedWithdrawal.amount_to_pay} USDT
                    </div>
                  )}
                </div>
                <div>
                  <div className="mb-1 text-gray-500">Метод</div>
                  <div className="font-mono text-white uppercase">
                    {selectedWithdrawal.payment_method || "КРИПТО"}
                  </div>
                </div>
                <div>
                  <div className="mb-1 text-gray-500">Пользователь</div>
                  <div className="font-mono text-white">
                    {selectedWithdrawal.first_name || selectedWithdrawal.username || "Неизвестно"}
                  </div>
                  {selectedWithdrawal.telegram_id && (
                    <a
                      className="mt-1 flex items-center gap-1 text-pandora-cyan hover:text-pandora-cyan/80"
                      href={`tg://user?id=${selectedWithdrawal.telegram_id}`}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      <ExternalLink size={12} />
                      <span className="text-[10px]">Написать в Telegram</span>
                    </a>
                  )}
                </div>
                <div>
                  <div className="mb-1 text-gray-500">Баланс</div>
                  <div className="font-mono text-white">
                    {selectedWithdrawal.user_balance === undefined
                      ? "Н/Д"
                      : formatAmountWithCurrency(
                          selectedWithdrawal.user_balance,
                          selectedWithdrawal.balance_currency
                        )}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {/* Payment Details */}
              <div className="mb-6">
                <div className="mb-2 font-mono text-[10px] text-gray-500">РЕКВИЗИТЫ</div>
                <div className="border border-white/10 bg-black/50 p-4">
                  {selectedWithdrawal.payment_details?.details ? (
                    <div className="select-all break-all font-mono text-sm text-white">
                      {selectedWithdrawal.payment_details.details}
                    </div>
                  ) : (
                    <div className="text-gray-500 text-xs">Реквизиты не указаны</div>
                  )}
                </div>
              </div>

              {/* Admin Comment (if exists) */}
              {selectedWithdrawal.admin_comment && (
                <div className="mb-6">
                  <div className="mb-2 font-mono text-[10px] text-gray-500">КОММЕНТАРИЙ АДМИНА</div>
                  <div className="whitespace-pre-wrap border border-pandora-cyan/30 bg-pandora-cyan/10 p-4 text-gray-300 text-xs">
                    {selectedWithdrawal.admin_comment}
                  </div>
                </div>
              )}

              {/* Processed Info */}
              {selectedWithdrawal.processed_at && (
                <div className="mb-6">
                  <div className="mb-2 font-mono text-[10px] text-gray-500">ОБРАБОТАНО</div>
                  <div className="text-gray-400 text-xs">
                    {formatDate(selectedWithdrawal.processed_at)}
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            {renderActionButtons()}
          </>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center text-gray-600 opacity-50">
            <Wallet className="mb-4" size={48} />
            <span className="font-mono text-xs uppercase tracking-widest">Выберите заявку</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default memo(AdminWithdrawals);
