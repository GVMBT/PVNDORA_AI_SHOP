/**
 * OrderStatusBadge Component
 *
 * Displays order status with appropriate styling and animations.
 */

import type React from "react";
import { memo } from "react";

type RawOrderStatus =
  | "pending"
  | "prepaid"
  | "paid"
  | "partial"
  | "delivered"
  | "cancelled"
  | "refunded"
  | "expired"
  | "failed";
type AdaptedStatus = "paid" | "processing" | "refunded";

interface OrderStatusBadgeProps {
  rawStatus?: RawOrderStatus;
  status?: AdaptedStatus;
}

const OrderStatusBadge: React.FC<OrderStatusBadgeProps> = ({ rawStatus, status }) => {
  // Priority: rawStatus > status (fallback)

  if (rawStatus === "delivered") {
    return (
      <span className="border border-green-500/30 bg-green-500/20 px-2 py-0.5 font-bold text-[10px] text-green-400">
        [ DELIVERED ]
      </span>
    );
  }

  if (rawStatus === "paid") {
    return (
      <span className="animate-pulse border border-blue-500/30 bg-blue-500/20 px-2 py-0.5 font-bold text-[10px] text-blue-400">
        [ PROCESSING ]
      </span>
    );
  }

  if (rawStatus === "partial") {
    return (
      <span className="border border-yellow-500/30 bg-yellow-500/20 px-2 py-0.5 font-bold text-[10px] text-yellow-400">
        [ PARTIAL ]
      </span>
    );
  }

  if (rawStatus === "prepaid") {
    return (
      <span className="animate-pulse border border-purple-500/30 bg-purple-500/20 px-2 py-0.5 font-bold text-[10px] text-purple-400">
        [ PAID • WAITING_STOCK ]
      </span>
    );
  }

  if (rawStatus === "pending") {
    return (
      <span className="animate-pulse border border-orange-500/30 bg-orange-500/20 px-2 py-0.5 font-bold text-[10px] text-orange-400">
        [ UNPAID ]
      </span>
    );
  }

  if (rawStatus === "expired") {
    return (
      <span className="border border-gray-500/30 bg-gray-500/20 px-2 py-0.5 font-bold text-[10px] text-gray-400">
        [ EXPIRED ]
      </span>
    );
  }

  if (rawStatus === "cancelled" || rawStatus === "refunded") {
    return (
      <span className="border border-red-500/20 bg-red-500/10 px-2 py-0.5 font-bold text-[10px] text-red-500">
        [ {rawStatus.toUpperCase()} ]
      </span>
    );
  }

  if (rawStatus === "failed") {
    return (
      <span className="border border-red-500/30 bg-red-500/20 px-2 py-0.5 font-bold text-[10px] text-red-500">
        [ FAILED ]
      </span>
    );
  }

  // Fallback for old data without rawStatus
  if (!rawStatus && status === "paid") {
    return (
      <span className="border border-green-500/30 bg-green-500/20 px-2 py-0.5 font-bold text-[10px] text-green-400">
        [ STATUS: OK ]
      </span>
    );
  }

  if (!rawStatus && status === "processing") {
    return (
      <span className="animate-pulse border border-orange-500/30 bg-orange-500/20 px-2 py-0.5 font-bold text-[10px] text-orange-400">
        [ STATUS: PENDING ]
      </span>
    );
  }

  if (!rawStatus && status === "refunded") {
    return (
      <span className="border border-red-500/20 bg-red-500/10 px-2 py-0.5 font-bold text-[10px] text-red-500">
        [ STATUS: VOID ]
      </span>
    );
  }

  return null;
};

export default memo(OrderStatusBadge);
