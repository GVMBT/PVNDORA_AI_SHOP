/**
 * OrderStatusBadge Component
 * 
 * Displays order status with appropriate styling and animations.
 */

import React, { memo } from 'react';

type RawOrderStatus = 'pending' | 'prepaid' | 'paid' | 'partial' | 'delivered' | 'cancelled' | 'refunded' | 'expired' | 'failed';
type AdaptedStatus = 'paid' | 'processing' | 'refunded';

interface OrderStatusBadgeProps {
  rawStatus?: RawOrderStatus;
  status?: AdaptedStatus;
}

const OrderStatusBadge: React.FC<OrderStatusBadgeProps> = ({ rawStatus, status }) => {
  // Priority: rawStatus > status (fallback)
  
  if (rawStatus === 'delivered') {
    return (
      <span className="text-[10px] font-bold bg-green-500/20 text-green-400 px-2 py-0.5 border border-green-500/30">
        [ DELIVERED ]
      </span>
    );
  }
  
  if (rawStatus === 'paid') {
    return (
      <span className="text-[10px] font-bold bg-blue-500/20 text-blue-400 px-2 py-0.5 border border-blue-500/30 animate-pulse">
        [ PROCESSING ]
      </span>
    );
  }
  
  if (rawStatus === 'partial') {
    return (
      <span className="text-[10px] font-bold bg-yellow-500/20 text-yellow-400 px-2 py-0.5 border border-yellow-500/30">
        [ PARTIAL ]
      </span>
    );
  }
  
  if (rawStatus === 'prepaid') {
    return (
      <span className="text-[10px] font-bold bg-purple-500/20 text-purple-400 px-2 py-0.5 border border-purple-500/30 animate-pulse">
        [ PAID • WAITING_STOCK ]
      </span>
    );
  }
  
  if (rawStatus === 'pending') {
    return (
      <span className="text-[10px] font-bold bg-orange-500/20 text-orange-400 px-2 py-0.5 border border-orange-500/30 animate-pulse">
        [ UNPAID ]
      </span>
    );
  }
  
  if (rawStatus === 'expired') {
    return (
      <span className="text-[10px] font-bold bg-gray-500/20 text-gray-400 px-2 py-0.5 border border-gray-500/30">
        [ EXPIRED ]
      </span>
    );
  }
  
  if (rawStatus === 'cancelled' || rawStatus === 'refunded') {
    return (
      <span className="text-[10px] font-bold bg-red-500/10 text-red-500 px-2 py-0.5 border border-red-500/20">
        [ {rawStatus.toUpperCase()} ]
      </span>
    );
  }
  
  if (rawStatus === 'failed') {
    return (
      <span className="text-[10px] font-bold bg-red-500/20 text-red-500 px-2 py-0.5 border border-red-500/30">
        [ FAILED ]
      </span>
    );
  }
  
  // Fallback for old data without rawStatus
  if (!rawStatus && status === 'paid') {
    return (
      <span className="text-[10px] font-bold bg-green-500/20 text-green-400 px-2 py-0.5 border border-green-500/30">
        [ STATUS: OK ]
      </span>
    );
  }
  
  if (!rawStatus && status === 'processing') {
    return (
      <span className="text-[10px] font-bold bg-orange-500/20 text-orange-400 px-2 py-0.5 border border-orange-500/30 animate-pulse">
        [ STATUS: PENDING ]
      </span>
    );
  }
  
  if (!rawStatus && status === 'refunded') {
    return (
      <span className="text-[10px] font-bold bg-red-500/10 text-red-500 px-2 py-0.5 border border-red-500/20">
        [ STATUS: VOID ]
      </span>
    );
  }
  
  return null;
};

export default memo(OrderStatusBadge);












