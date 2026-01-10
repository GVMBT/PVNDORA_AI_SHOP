/**
 * StatusBadge Component
 * 
 * Displays a status badge with appropriate styling based on status value.
 */

import React, { memo } from 'react';

interface StatusBadgeProps {
  status: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getColor = (s: string) => {
    switch(s.toUpperCase()) {
      // Order statuses - green (completed)
      case 'DELIVERED':
      case 'PAID': 
      case 'ACTIVE': 
      case 'OPEN': 
        return 'text-green-500 bg-green-500/10 border-green-500/20';
      
      // Order statuses - orange (in progress)
      case 'PARTIAL':
        return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
      case 'PREPAID':
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'PENDING':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      
      // Order statuses - red (cancelled/refunded)
      case 'REFUNDED':
      case 'CANCELLED': 
      case 'INACTIVE': 
      case 'CLOSED': 
        return 'text-red-500 bg-red-500/10 border-red-500/20';
      
      // User roles
      case 'VIP': 
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      case 'ADMIN':
        return 'text-pandora-cyan bg-pandora-cyan/10 border-pandora-cyan/20';
      
      default: 
        return 'text-gray-400 bg-gray-500/10 border-gray-500/20';
    }
  };

  return (
    <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${getColor(status)}`}>
      {status.toUpperCase()}
    </span>
  );
};

export default memo(StatusBadge);





































