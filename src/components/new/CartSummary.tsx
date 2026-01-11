/**
 * CartSummary Component
 * 
 * Displays cart items and total summary in checkout modal.
 */

import React, { memo, useState } from 'react';
import { motion } from 'framer-motion';
import { Trash2, ChevronRight, Tag, Loader2, Check, X, Minus, Plus } from 'lucide-react';
import { formatPrice } from '../../utils/currency';
import { useLocale } from '../../hooks/useLocale';
import type { CartItem } from '../../types/component';

interface CartSummaryProps {
  cart: CartItem[];
  total: number;
  originalTotal?: number;
  currency: string;
  promoCode?: string | null;
  promoDiscountPercent?: number | null;
  onRemoveItem: (id: string | number) => void;
  onUpdateQuantity?: (id: string | number, quantity: number) => void;
  onProceed: () => void;
  onApplyPromo?: (code: string) => Promise<{ success: boolean; message?: string }>;
  onRemovePromo?: () => void;
}

const CartSummary: React.FC<CartSummaryProps> = ({
  cart,
  total,
  originalTotal,
  currency,
  promoCode,
  promoDiscountPercent,
  onRemoveItem,
  onUpdateQuantity,
  onProceed,
  onApplyPromo,
  onRemovePromo,
}) => {
  const { t } = useLocale();
  const [promoInput, setPromoInput] = useState('');
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoError, setPromoError] = useState<string | null>(null);
  
  const handleApplyPromo = async () => {
    if (!promoInput.trim() || !onApplyPromo) return;
    
    setPromoLoading(true);
    setPromoError(null);
    
    try {
      const result = await onApplyPromo(promoInput.trim().toUpperCase());
      if (!result.success) {
        setPromoError(result.message || t('checkout.promoInvalid'));
      } else {
        setPromoInput('');
      }
    } catch {
      setPromoError(t('checkout.promoFailed'));
    } finally {
      setPromoLoading(false);
    }
  };
  
  const discount = originalTotal && originalTotal > total ? originalTotal - total : 0;
  
  if (cart.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-600 font-mono mb-4">{t('checkout.cartEmpty').toUpperCase()}</div>
        <button onClick={onProceed} className="text-pandora-cyan font-bold hover:underline">
          {t('checkout.returnToCatalog').toUpperCase()}
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
      <div className="space-y-3">
        {cart.map((item) => {
          const quantity = item.quantity || 1;
          return (
            <div 
              key={item.id} 
              className="group bg-white/[0.03] border border-white/10 p-3 rounded-sm hover:border-pandora-cyan/30 transition-all duration-300"
            >
              <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                {/* Product Info: Image, Name, Category */}
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 bg-black border border-white/10 rounded-sm overflow-hidden flex-shrink-0">
                    <img 
                      src={item.image} 
                      className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500" 
                      alt={item.name} 
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-bold text-white text-sm sm:text-base truncate group-hover:text-pandora-cyan transition-colors">
                      {item.name}
                    </div>
                    <div className="text-[10px] text-gray-500 font-mono uppercase tracking-wider">
                      {item.category}
                    </div>
                  </div>
                  
                  {/* Trash for Mobile Only */}
                  <button 
                    type="button"
                    onClick={() => onRemoveItem(item.id)} 
                    className="sm:hidden text-gray-600 hover:text-red-500 transition-colors p-1 flex-shrink-0"
                    aria-label="Remove item"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                
                {/* Controls & Price Section */}
                <div className="flex items-center justify-between sm:items-center sm:justify-end gap-4 sm:gap-8 pt-3 sm:pt-0 border-t border-white/5 sm:border-0">
                  {/* Quantity Controls */}
                  {onUpdateQuantity ? (
                    <div className="flex items-center bg-black/50 border border-white/10 rounded-sm overflow-hidden h-9 flex-shrink-0">
                      <button
                        type="button"
                        onClick={() => {
                          if (quantity > 1) {
                            onUpdateQuantity(item.id, quantity - 1);
                          }
                        }}
                        disabled={quantity <= 1}
                        className="w-8 h-full flex items-center justify-center text-gray-400 hover:text-pandora-cyan hover:bg-white/5 disabled:opacity-20 disabled:cursor-not-allowed transition-colors"
                        aria-label="Decrease quantity"
                      >
                        <Minus size={12} />
                      </button>
                      <span className="w-8 h-full flex items-center justify-center text-xs font-mono text-white border-x border-white/10">
                        {quantity}
                      </span>
                      <button
                        type="button"
                        onClick={() => onUpdateQuantity(item.id, quantity + 1)}
                        className="w-8 h-full flex items-center justify-center text-gray-400 hover:text-pandora-cyan hover:bg-white/5 transition-colors"
                        aria-label="Increase quantity"
                      >
                        <Plus size={12} />
                      </button>
                    </div>
                  ) : (
                    <div className="text-[10px] text-gray-500 font-mono bg-white/5 px-2 py-1 rounded-sm">
                      QTY: {quantity}
                    </div>
                  )}
                  
                  {/* Price & Delete (Desktop) */}
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="font-mono text-pandora-cyan font-bold text-sm sm:text-base whitespace-nowrap">
                        {formatPrice(item.price * quantity, item.currency || currency)}
                      </div>
                      {quantity > 1 && (
                        <div className="text-[9px] text-gray-500 font-mono tracking-tighter">
                          {formatPrice(item.price, item.currency || currency)} / {t('checkout.each')}
                        </div>
                      )}
                    </div>
                    
                    {/* Trash for Desktop Only */}
                    <button 
                      type="button"
                      onClick={() => onRemoveItem(item.id)} 
                      className="hidden sm:flex text-gray-600 hover:text-red-500 transition-colors p-2 flex-shrink-0 items-center justify-center hover:bg-red-500/10 rounded-sm"
                      aria-label="Remove item"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 border-t border-white/10 pt-6">
        {/* Promo Code Section */}
        {onApplyPromo && (
          <div className="mb-6">
            {promoCode ? (
              <div className="flex items-center justify-between bg-pandora-cyan/10 border border-pandora-cyan/30 p-3 rounded-sm">
                <div className="flex items-center gap-2">
                  <Tag size={14} className="text-pandora-cyan" />
                  <span className="font-mono text-sm text-pandora-cyan">{promoCode}</span>
                  {promoDiscountPercent && (
                    <span className="text-xs text-green-400">-{promoDiscountPercent}%</span>
                  )}
                </div>
                {onRemovePromo && (
                  <button 
                    onClick={onRemovePromo}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  type="text"
                  value={promoInput}
                  onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                  placeholder="PROMO_CODE"
                  className="flex-1 bg-black border border-white/20 px-4 py-2 text-white font-mono text-sm placeholder-gray-600 focus:border-pandora-cyan focus:outline-none"
                />
                <button
                  onClick={handleApplyPromo}
                  disabled={promoLoading || !promoInput.trim()}
                  className="px-4 py-2 bg-white/10 border border-white/20 text-white font-mono text-sm hover:bg-pandora-cyan/20 hover:border-pandora-cyan/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                  {promoLoading ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  {t('checkout.apply').toUpperCase()}
                </button>
              </div>
            )}
            {promoError && (
              <div className="mt-2 text-xs text-red-400 font-mono">{promoError}</div>
            )}
          </div>
        )}
        
        {/* Totals */}
        <div className="space-y-2 mb-6">
          {discount > 0 && originalTotal && (
            <>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500 font-mono">{t('checkout.subtotal').toUpperCase()}</span>
                <span className="text-gray-400 line-through">{formatPrice(originalTotal, currency)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-green-400 font-mono">{t('checkout.discount').toUpperCase()}</span>
                <span className="text-green-400">-{formatPrice(discount, currency)}</span>
              </div>
            </>
          )}
          <div className="flex justify-between items-end">
            <span className="text-gray-500 font-mono text-xs">{t('checkout.total').toUpperCase()}</span>
            <span className="text-3xl font-display font-bold text-white">
              {formatPrice(total, currency)}
            </span>
          </div>
        </div>
        
        <button 
          onClick={onProceed}
          className="w-full bg-white text-black font-bold py-4 hover:bg-pandora-cyan transition-colors uppercase tracking-widest flex items-center justify-center gap-2 group"
        >
          {t('checkout.proceedToPayment').toUpperCase()}
          <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </motion.div>
  );
};

export default memo(CartSummary);







