/**
 * StockIndicator Component
 *
 * Displays stock status with visual indicator.
 */

import type React from "react";
import { memo } from "react";

interface StockIndicatorProps {
  stock: number;
}

const StockIndicator: React.FC<StockIndicatorProps> = ({ stock }) => (
  <div className="flex items-center gap-2">
    <div className={`h-2 w-2 rounded-full ${stock > 0 ? "bg-green-500" : "bg-red-500"}`} />
    <span className={`font-mono text-xs ${stock > 0 ? "text-white" : "text-red-500"}`}>
      {stock} units
    </span>
  </div>
);

export default memo(StockIndicator);
