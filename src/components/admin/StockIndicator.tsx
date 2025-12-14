/**
 * StockIndicator Component
 * 
 * Displays stock status with visual indicator.
 */

import React, { memo } from 'react';

interface StockIndicatorProps {
  stock: number;
}

const StockIndicator: React.FC<StockIndicatorProps> = ({ stock }) => (
  <div className="flex items-center gap-2">
    <div className={`w-2 h-2 rounded-full ${stock > 0 ? 'bg-green-500' : 'bg-red-500'}`} />
    <span className={`text-xs font-mono ${stock > 0 ? 'text-white' : 'text-red-500'}`}>
      {stock} units
    </span>
  </div>
);

export default memo(StockIndicator);

