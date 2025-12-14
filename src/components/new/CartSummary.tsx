/**
 * CartSummary Component
 * 
 * Displays cart items and total summary in checkout modal.
 */

import React, { memo } from 'react';
import { motion } from 'framer-motion';
import { Trash2, ChevronRight } from 'lucide-react';
import { formatPrice } from '../../utils/currency';
import type { CartItem } from '../../types/component';

interface CartSummaryProps {
  cart: CartItem[];
  total: number;
  currency: string;
  onRemoveItem: (id: string | number) => void;
  onProceed: () => void;
}

const CartSummary: React.FC<CartSummaryProps> = ({
  cart,
  total,
  currency,
  onRemoveItem,
  onProceed,
}) => {
  if (cart.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-600 font-mono mb-4">NO_MODULES_DETECTED</div>
        <button onClick={onProceed} className="text-pandora-cyan font-bold hover:underline">
          RETURN TO CATALOG
        </button>
      </div>
    );
  }

  return (
    <motion.div 
      key="cart"
      initial={{ opacity: 0, x: -20 }} 
      animate={{ opacity: 1, x: 0 }} 
      exit={{ opacity: 0, x: -20 }}
    >
      <div className="space-y-4">
        {cart.map((item) => (
          <div 
            key={item.id} 
            className="flex items-center justify-between bg-white/5 border border-white/10 p-4 rounded-sm hover:border-pandora-cyan/30 transition-colors"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-black border border-white/10 rounded-sm overflow-hidden relative">
                <img src={item.image} className="w-full h-full object-cover grayscale" alt={item.name} />
                {(item.quantity || 1) > 1 && (
                  <div className="absolute top-0 right-0 bg-pandora-cyan text-black text-[9px] font-bold w-4 h-4 flex items-center justify-center">
                    {item.quantity}
                  </div>
                )}
              </div>
              <div>
                <div className="font-bold text-white text-sm">{item.name}</div>
                <div className="text-[10px] text-gray-500 font-mono flex items-center gap-2">
                  {item.category} MODULE
                  {(item.quantity || 1) > 1 && (
                    <span className="text-white">x{item.quantity}</span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <div className="font-mono text-pandora-cyan">
                  {formatPrice(item.price * (item.quantity || 1), item.currency || currency)}
                </div>
                {(item.quantity || 1) > 1 && (
                  <div className="text-[9px] text-gray-500">
                    {formatPrice(item.price, item.currency || currency)} ea
                  </div>
                )}
              </div>
              <button 
                onClick={() => onRemoveItem(item.id)} 
                className="text-gray-600 hover:text-red-500 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 border-t border-white/10 pt-6">
        <div className="flex justify-between items-end mb-6">
          <span className="text-gray-500 font-mono text-xs">TOTAL_ESTIMATION</span>
          <span className="text-3xl font-display font-bold text-white">
            {formatPrice(total, currency)}
          </span>
        </div>
        <button 
          onClick={onProceed}
          className="w-full bg-white text-black font-bold py-4 hover:bg-pandora-cyan transition-colors uppercase tracking-widest flex items-center justify-center gap-2 group"
        >
          PROCEED TO PAYMENT 
          <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </motion.div>
  );
};

export default memo(CartSummary);



