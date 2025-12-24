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
      case 'PAID': 
      case 'ACTIVE': 
      case 'OPEN': 
        return 'text-green-500 bg-green-500/10 border-green-500/20';
      case 'REFUNDED': 
      case 'INACTIVE': 
      case 'CLOSED': 
        return 'text-red-500 bg-red-500/10 border-red-500/20';
      case 'VIP': 
        return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
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


































