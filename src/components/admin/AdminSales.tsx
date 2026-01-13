/**
 * AdminSales Component
 *
 * Sales and orders management view.
 */

import React, { useState, useMemo, memo, useCallback } from "react";
import { Search, RefreshCw, CheckCircle, XCircle } from "lucide-react";
import StatusBadge from "./StatusBadge";
import type { OrderData } from "./types";
import { apiRequest } from "../../utils/apiClient";
import { API } from "../../config";
import { logger } from "../../utils/logger";

interface AdminSalesProps {
  orders: OrderData[];
  onRefresh?: () => void;
}

// Helper functions to avoid nested ternaries
const getSourceChannelStyle = (channel: string): string => {
  if (channel === "discount") return "bg-yellow-500/20 text-yellow-400";
  if (channel === "webapp") return "bg-blue-500/20 text-blue-400";
  return "bg-pandora-cyan/20 text-pandora-cyan";
};

const getSourceChannelLabel = (channel: string, short = false): string => {
  if (channel === "discount") return short ? "DSC" : "DISCOUNT";
  if (channel === "webapp") return short ? "WEB" : "WEBAPP";
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
        const result = await apiRequest<any>(`${API.ADMIN_URL}/orders/${orderId}/check-payment`);
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
        const result = await apiRequest<any>(`${API.ADMIN_URL}/orders/${orderId}/force-status`, {
          method: "POST",
          body: JSON.stringify({ new_status: newStatus }),
        });

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
      <div className="flex flex-col md:flex-row justify-between items-center gap-4">
        <h3 className="font-display font-bold text-white uppercase text-lg">Заказы</h3>
        <div className="flex items-center gap-2">
          {pendingOrders.length > 0 && (
            <div className="text-xs text-yellow-400 font-mono">
              ⚠️ {pendingOrders.length} требуют внимания
            </div>
          )}
          <div className="relative w-full md:w-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
            <input
              type="text"
              placeholder="Поиск Order ID или User..."
              value={orderSearch}
              onChange={(e) => setOrderSearch(e.target.value)}
              className="w-full md:w-64 bg-[#0e0e0e] border border-white/20 pl-9 pr-4 py-2 text-xs font-mono text-white focus:border-pandora-cyan outline-none"
            />
          </div>
        </div>
      </div>

      <div className="hidden md:block bg-[#0e0e0e] border border-white/10 rounded-sm overflow-hidden">
        <table className="w-full text-left text-xs font-mono">
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
                  key={o.id}
                  className={`hover:bg-white/5 transition-colors ${isPending ? "bg-yellow-500/5" : ""}`}
                >
                  <td className="p-4 font-bold text-pandora-cyan">{o.id}</td>
                  <td className="p-4 text-gray-400">{o.user}</td>
                  <td className="p-4 font-bold text-white">{o.product}</td>
                  <td className="p-4">
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded ${getSourceChannelStyle(o.source_channel)}`}
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
                          onClick={(e) => {
                            e.stopPropagation();
                            handleCheckPayment(o.id);
                          }}
                          disabled={isChecking || isProcessing}
                          className="p-1.5 bg-blue-500/20 border border-blue-500/50 rounded hover:bg-blue-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Проверить оплату"
                        >
                          <RefreshCw
                            size={12}
                            className={`text-blue-400 ${isChecking ? "animate-spin" : ""}`}
                          />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleForceStatus(o.id, "paid");
                          }}
                          disabled={isChecking || isProcessing}
                          className="p-1.5 bg-green-500/20 border border-green-500/50 rounded hover:bg-green-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Отметить оплаченным"
                        >
                          <CheckCircle size={12} className="text-green-400" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleForceStatus(o.id, "cancelled");
                          }}
                          disabled={isChecking || isProcessing}
                          className="p-1.5 bg-red-500/20 border border-red-500/50 rounded hover:bg-red-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Отменить заказ"
                        >
                          <XCircle size={12} className="text-red-400" />
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
      <div className="md:hidden space-y-4">
        {filteredOrders.map((o) => {
          const isPending = o.status === "PENDING";
          const isChecking = checkingOrderId === o.id;
          const isProcessing = processingOrderId === o.id;

          return (
            <div
              key={o.id}
              className={`bg-[#0e0e0e] border ${isPending ? "border-yellow-500/30" : "border-white/10"} p-4 space-y-3`}
            >
              <div className="flex justify-between items-center">
                <span className="font-bold text-pandora-cyan text-sm">{o.id}</span>
                <span className="text-[10px] text-gray-500">{o.date}</span>
              </div>
              <div className="text-sm text-white font-bold">{o.product}</div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400">{o.user}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded ${getSourceChannelStyle(o.source_channel)}`}
                  >
                    {getSourceChannelLabel(o.source_channel, true)}
                  </span>
                  <StatusBadge status={o.status} />
                </div>
              </div>
              {isPending && (
                <div className="flex gap-2 pt-2 border-t border-white/10">
                  <button
                    onClick={() => handleCheckPayment(o.id)}
                    disabled={isChecking || isProcessing}
                    className="flex-1 px-3 py-1.5 bg-blue-500/20 border border-blue-500/50 rounded text-xs text-blue-400 hover:bg-blue-500/30 transition-colors disabled:opacity-50"
                  >
                    {isChecking ? "Проверка..." : "Проверить оплату"}
                  </button>
                  <button
                    onClick={() => handleForceStatus(o.id, "paid")}
                    disabled={isChecking || isProcessing}
                    className="flex-1 px-3 py-1.5 bg-green-500/20 border border-green-500/50 rounded text-xs text-green-400 hover:bg-green-500/30 transition-colors disabled:opacity-50"
                  >
                    Оплачен
                  </button>
                  <button
                    onClick={() => handleForceStatus(o.id, "cancelled")}
                    disabled={isChecking || isProcessing}
                    className="flex-1 px-3 py-1.5 bg-red-500/20 border border-red-500/50 rounded text-xs text-red-400 hover:bg-red-500/30 transition-colors disabled:opacity-50"
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
