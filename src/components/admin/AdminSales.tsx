/**
 * AdminSales Component
 *
 * Sales and orders management view.
 */

import { CheckCircle, RefreshCw, Search, XCircle } from "lucide-react";
import type React from "react";
import { memo, useCallback, useMemo, useState } from "react";
import { API } from "../../config";
import { apiRequest } from "../../utils/apiClient";
import { logger } from "../../utils/logger";
import StatusBadge from "./StatusBadge";
import type { OrderData } from "./types";

interface AdminSalesProps {
  orders: OrderData[];
  onRefresh?: () => void;
}

interface CheckPaymentResponse {
  invoice_state?: string;
  current_status: string;
  message: string;
}

interface ForceStatusResponse {
  success: boolean;
  message: string;
}

// Helper functions to avoid nested ternaries
const getSourceChannelStyle = (channel: string): string => {
  if (channel === "discount") {
    return "bg-yellow-500/20 text-yellow-400";
  }
  if (channel === "webapp") {
    return "bg-blue-500/20 text-blue-400";
  }
  return "bg-pandora-cyan/20 text-pandora-cyan";
};

const getSourceChannelLabel = (channel: string, short = false): string => {
  if (channel === "discount") {
    return short ? "DSC" : "DISCOUNT";
  }
  if (channel === "webapp") {
    return short ? "WEB" : "WEBAPP";
  }
  return short ? "PVN" : "PVNDORA";
};

const AdminSales: React.FC<AdminSalesProps> = ({ orders, onRefresh }) => {
  const [orderSearch, setOrderSearch] = useState("");
  const [checkingOrderId, setCheckingOrderId] = useState<string | null>(null);
  const [processingOrderId, setProcessingOrderId] = useState<string | null>(null);

  const filteredOrders = useMemo(() => {
    return orders.filter(
      (o) =>
        o.id.toLowerCase().includes(orderSearch.toLowerCase()) ||
        o.user.toLowerCase().includes(orderSearch.toLowerCase())
    );
  }, [orders, orderSearch]);

  const handleCheckPayment = useCallback(
    async (orderId: string) => {
      setCheckingOrderId(orderId);
      try {
        const result = await apiRequest<CheckPaymentResponse>(
          `${API.ADMIN_URL}/orders/${orderId}/check-payment`
        );
        logger.info("Payment check result", result);

        alert(
          `Статус инвойса: ${result.invoice_state || "unknown"}\nТекущий статус заказа: ${result.current_status}\n\n${result.message}`
        );

        if (onRefresh) {
          onRefresh();
        }
      } catch (err) {
        logger.error("Failed to check payment", err);
        alert(`Ошибка: ${err instanceof Error ? err.message : "Unknown error"}`);
      } finally {
        setCheckingOrderId(null);
      }
    },
    [onRefresh]
  );

  const handleForceStatus = useCallback(
    async (orderId: string, newStatus: string) => {
      if (!confirm(`Обновить статус заказа на "${newStatus}"?`)) {
        return;
      }

      setProcessingOrderId(orderId);
      try {
        const result = await apiRequest<ForceStatusResponse>(
          `${API.ADMIN_URL}/orders/${orderId}/force-status`,
          {
            method: "POST",
            body: JSON.stringify({ new_status: newStatus }),
          }
        );

        logger.info("Force status result", result);
        alert(result.message || "Статус обновлён");

        if (onRefresh) {
          onRefresh();
        }
      } catch (err) {
        logger.error("Failed to force status", err);
        alert(`Ошибка: ${err instanceof Error ? err.message : "Unknown error"}`);
      } finally {
        setProcessingOrderId(null);
      }
    },
    [onRefresh]
  );

  const pendingOrders = useMemo(
    () => filteredOrders.filter((o) => o.status === "PENDING"),
    [filteredOrders]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
        <h3 className="font-bold font-display text-lg text-white uppercase">Заказы</h3>
        <div className="flex items-center gap-2">
          {pendingOrders.length > 0 && (
            <div className="font-mono text-xs text-yellow-400">
              ⚠️ {pendingOrders.length} требуют внимания
            </div>
          )}
          <div className="relative w-full md:w-auto">
            <Search className="absolute top-1/2 left-3 -translate-y-1/2 text-gray-500" size={14} />
            <input
              className="w-full border border-white/20 bg-[#0e0e0e] py-2 pr-4 pl-9 font-mono text-white text-xs outline-none focus:border-pandora-cyan md:w-64"
              onChange={(e) => setOrderSearch(e.target.value)}
              placeholder="Поиск Order ID или User..."
              type="text"
              value={orderSearch}
            />
          </div>
        </div>
      </div>

      <div className="hidden overflow-hidden rounded-sm border border-white/10 bg-[#0e0e0e] md:block">
        <table className="w-full text-left font-mono text-xs">
          <thead className="bg-white/5 text-gray-400 uppercase">
            <tr>
              <th className="p-4">Order ID</th>
              <th className="p-4">User</th>
              <th className="p-4">Product</th>
              <th className="p-4">Source</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Date</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-gray-300">
            {filteredOrders.map((o) => {
              const isPending = o.status === "PENDING";
              const isChecking = checkingOrderId === o.id;
              const isProcessing = processingOrderId === o.id;

              return (
                <tr
                  className={`transition-colors hover:bg-white/5 ${isPending ? "bg-yellow-500/5" : ""}`}
                  key={o.id}
                >
                  <td className="p-4 font-bold text-pandora-cyan">{o.id}</td>
                  <td className="p-4 text-gray-400">{o.user}</td>
                  <td className="p-4 font-bold text-white">{o.product}</td>
                  <td className="p-4">
                    <span
                      className={`rounded px-2 py-0.5 font-mono text-[10px] ${getSourceChannelStyle(o.source_channel)}`}
                    >
                      {getSourceChannelLabel(o.source_channel)}
                    </span>
                  </td>
                  <td className="p-4">
                    <StatusBadge status={o.status} />
                  </td>
                  <td className="p-4 text-right text-gray-500">{o.date}</td>
                  <td className="p-4 text-right">
                    {isPending && (
                      <div className="flex items-center justify-end gap-1">
                        <button
                          className="rounded border border-blue-500/50 bg-blue-500/20 p-1.5 transition-colors hover:bg-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isChecking || isProcessing}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCheckPayment(o.id);
                          }}
                          title="Проверить оплату"
                          type="button"
                        >
                          <RefreshCw
                            className={`text-blue-400 ${isChecking ? "animate-spin" : ""}`}
                            size={12}
                          />
                        </button>
                        <button
                          className="rounded border border-green-500/50 bg-green-500/20 p-1.5 transition-colors hover:bg-green-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isChecking || isProcessing}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleForceStatus(o.id, "paid");
                          }}
                          title="Отметить оплаченным"
                          type="button"
                        >
                          <CheckCircle className="text-green-400" size={12} />
                        </button>
                        <button
                          className="rounded border border-red-500/50 bg-red-500/20 p-1.5 transition-colors hover:bg-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isChecking || isProcessing}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleForceStatus(o.id, "cancelled");
                          }}
                          title="Отменить заказ"
                          type="button"
                        >
                          <XCircle className="text-red-400" size={12} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile Orders */}
      <div className="space-y-4 md:hidden">
        {filteredOrders.map((o) => {
          const isPending = o.status === "PENDING";
          const isChecking = checkingOrderId === o.id;
          const isProcessing = processingOrderId === o.id;

          return (
            <div
              className={`border bg-[#0e0e0e] ${isPending ? "border-yellow-500/30" : "border-white/10"} space-y-3 p-4`}
              key={o.id}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-pandora-cyan text-sm">{o.id}</span>
                <span className="text-[10px] text-gray-500">{o.date}</span>
              </div>
              <div className="font-bold text-sm text-white">{o.product}</div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-400">{o.user}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-2 py-0.5 font-mono text-[10px] ${getSourceChannelStyle(o.source_channel)}`}
                  >
                    {getSourceChannelLabel(o.source_channel, true)}
                  </span>
                  <StatusBadge status={o.status} />
                </div>
              </div>
              {isPending && (
                <div className="flex gap-2 border-white/10 border-t pt-2">
                  <button
                    className="flex-1 rounded border border-blue-500/50 bg-blue-500/20 px-3 py-1.5 text-blue-400 text-xs transition-colors hover:bg-blue-500/30 disabled:opacity-50"
                    disabled={isChecking || isProcessing}
                    onClick={() => handleCheckPayment(o.id)}
                    type="button"
                  >
                    {isChecking ? "Проверка..." : "Проверить оплату"}
                  </button>
                  <button
                    className="flex-1 rounded border border-green-500/50 bg-green-500/20 px-3 py-1.5 text-green-400 text-xs transition-colors hover:bg-green-500/30 disabled:opacity-50"
                    disabled={isChecking || isProcessing}
                    onClick={() => handleForceStatus(o.id, "paid")}
                    type="button"
                  >
                    Оплачен
                  </button>
                  <button
                    className="flex-1 rounded border border-red-500/50 bg-red-500/20 px-3 py-1.5 text-red-400 text-xs transition-colors hover:bg-red-500/30 disabled:opacity-50"
                    disabled={isChecking || isProcessing}
                    onClick={() => handleForceStatus(o.id, "cancelled")}
                    type="button"
                  >
                    Отменить
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default memo(AdminSales);
