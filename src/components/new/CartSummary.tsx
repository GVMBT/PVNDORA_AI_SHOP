/**
 * CartSummary Component
 *
 * Displays cart items and total summary in checkout modal.
 */

import { motion } from "framer-motion";
import { Check, ChevronRight, Loader2, Minus, Plus, Tag, Trash2, X } from "lucide-react";
import type React from "react";
import { memo, useState } from "react";
import { useLocale } from "../../hooks/useLocale";
import type { CartItem } from "../../types/component";
import { formatPrice } from "../../utils/currency";

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
  const [promoInput, setPromoInput] = useState("");
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoError, setPromoError] = useState<string | null>(null);

  const handleApplyPromo = async () => {
    if (!(promoInput.trim() && onApplyPromo)) return;

    setPromoLoading(true);
    setPromoError(null);

    try {
      const result = await onApplyPromo(promoInput.trim().toUpperCase());
      if (result.success) {
        setPromoInput("");
      } else {
        setPromoError(result.message || t("checkout.promoInvalid"));
      }
    } catch {
      setPromoError(t("checkout.promoFailed"));
    } finally {
      setPromoLoading(false);
    }
  };

  const discount = originalTotal && originalTotal > total ? originalTotal - total : 0;

  if (cart.length === 0) {
    return (
      <div className="py-12 text-center">
        <div className="mb-4 font-mono text-gray-600">{t("checkout.cartEmpty").toUpperCase()}</div>
        <button
          className="font-bold text-pandora-cyan hover:underline"
          onClick={onProceed}
          type="button"
        >
          {t("checkout.returnToCatalog").toUpperCase()}
        </button>
      </div>
    );
  }

  return (
    <motion.div
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      initial={{ opacity: 0, x: -20 }}
      key="cart"
    >
      <div className="space-y-3">
        {cart.map((item) => {
          const quantity = item.quantity || 1;
          return (
            <div
              className="group rounded-sm border border-white/10 bg-white/[0.03] p-3 transition-all duration-300 hover:border-pandora-cyan/30"
              key={item.id}
            >
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                {/* Product Info: Image, Name, Category */}
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <div className="h-10 w-10 flex-shrink-0 overflow-hidden rounded-sm border border-white/10 bg-black sm:h-12 sm:w-12">
                    <img
                      alt={item.name}
                      className="h-full w-full object-cover grayscale transition-all duration-500 group-hover:grayscale-0"
                      src={item.image}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-bold text-sm text-white transition-colors group-hover:text-pandora-cyan sm:text-base">
                      {item.name}
                    </div>
                    <div className="font-mono text-[10px] text-gray-500 uppercase tracking-wider">
                      {item.category}
                    </div>
                  </div>

                  {/* Trash for Mobile Only */}
                  <button
                    aria-label="Remove item"
                    className="flex-shrink-0 p-1 text-gray-600 transition-colors hover:text-red-500 sm:hidden"
                    onClick={() => onRemoveItem(item.id)}
                    type="button"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                {/* Controls & Price Section */}
                <div className="flex items-center justify-between gap-4 border-white/5 border-t pt-3 sm:items-center sm:justify-end sm:gap-8 sm:border-0 sm:pt-0">
                  {/* Quantity Controls */}
                  {onUpdateQuantity ? (
                    <div className="flex h-9 flex-shrink-0 items-center overflow-hidden rounded-sm border border-white/10 bg-black/50">
                      <button
                        aria-label="Decrease quantity"
                        className="flex h-full w-8 items-center justify-center text-gray-400 transition-colors hover:bg-white/5 hover:text-pandora-cyan disabled:cursor-not-allowed disabled:opacity-20"
                        disabled={quantity <= 1}
                        onClick={() => {
                          if (quantity > 1) {
                            onUpdateQuantity(item.id, quantity - 1);
                          }
                        }}
                        type="button"
                      >
                        <Minus size={12} />
                      </button>
                      <span className="flex h-full w-8 items-center justify-center border-white/10 border-x font-mono text-white text-xs">
                        {quantity}
                      </span>
                      <button
                        aria-label="Increase quantity"
                        className="flex h-full w-8 items-center justify-center text-gray-400 transition-colors hover:bg-white/5 hover:text-pandora-cyan"
                        onClick={() => onUpdateQuantity(item.id, quantity + 1)}
                        type="button"
                      >
                        <Plus size={12} />
                      </button>
                    </div>
                  ) : (
                    <div className="rounded-sm bg-white/5 px-2 py-1 font-mono text-[10px] text-gray-500">
                      QTY: {quantity}
                    </div>
                  )}

                  {/* Price & Delete (Desktop) */}
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="whitespace-nowrap font-bold font-mono text-pandora-cyan text-sm sm:text-base">
                        {formatPrice(item.price * quantity, item.currency || currency)}
                      </div>
                      {quantity > 1 && (
                        <div className="font-mono text-[9px] text-gray-500 tracking-tighter">
                          {formatPrice(item.price, item.currency || currency)} /{" "}
                          {t("checkout.each")}
                        </div>
                      )}
                    </div>

                    {/* Trash for Desktop Only */}
                    <button
                      aria-label="Remove item"
                      className="hidden flex-shrink-0 items-center justify-center rounded-sm p-2 text-gray-600 transition-colors hover:bg-red-500/10 hover:text-red-500 sm:flex"
                      onClick={() => onRemoveItem(item.id)}
                      type="button"
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

      <div className="mt-8 border-white/10 border-t pt-6">
        {/* Promo Code Section */}
        {onApplyPromo && (
          <div className="mb-6">
            {promoCode ? (
              <div className="flex items-center justify-between rounded-sm border border-pandora-cyan/30 bg-pandora-cyan/10 p-3">
                <div className="flex items-center gap-2">
                  <Tag className="text-pandora-cyan" size={14} />
                  <span className="font-mono text-pandora-cyan text-sm">{promoCode}</span>
                  {promoDiscountPercent && promoDiscountPercent > 0 && (
                    <span className="text-green-400 text-xs">-{promoDiscountPercent}%</span>
                  )}
                </div>
                {onRemovePromo && (
                  <button
                    className="text-gray-400 transition-colors hover:text-red-500"
                    onClick={onRemovePromo}
                    type="button"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            ) : (
              <div className="flex gap-2">
                <input
                  className="flex-1 border border-white/20 bg-black px-4 py-2 font-mono text-sm text-white placeholder-gray-600 focus:border-pandora-cyan focus:outline-none"
                  onChange={(e) => setPromoInput(e.target.value.toUpperCase())}
                  placeholder="PROMO_CODE"
                  type="text"
                  value={promoInput}
                />
                <button
                  className="flex items-center gap-2 border border-white/20 bg-white/10 px-4 py-2 font-mono text-sm text-white transition-colors hover:border-pandora-cyan/50 hover:bg-pandora-cyan/20 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={promoLoading || !promoInput.trim()}
                  onClick={handleApplyPromo}
                  type="button"
                >
                  {promoLoading ? (
                    <Loader2 className="animate-spin" size={14} />
                  ) : (
                    <Check size={14} />
                  )}
                  {t("checkout.apply").toUpperCase()}
                </button>
              </div>
            )}
            {promoError && <div className="mt-2 font-mono text-red-400 text-xs">{promoError}</div>}
          </div>
        )}

        {/* Totals */}
        <div className="mb-6 space-y-2">
          {discount > 0 && originalTotal && (
            <>
              <div className="flex justify-between text-sm">
                <span className="font-mono text-gray-500">
                  {t("checkout.subtotal").toUpperCase()}
                </span>
                <span className="text-gray-400 line-through">
                  {formatPrice(originalTotal, currency)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="font-mono text-green-400">
                  {t("checkout.discount").toUpperCase()}
                </span>
                <span className="text-green-400">-{formatPrice(discount, currency)}</span>
              </div>
            </>
          )}
          <div className="flex items-end justify-between">
            <span className="font-mono text-gray-500 text-xs">
              {t("checkout.total").toUpperCase()}
            </span>
            <span className="font-bold font-display text-3xl text-white">
              {formatPrice(total, currency)}
            </span>
          </div>
        </div>

        <button
          className="group flex w-full items-center justify-center gap-2 bg-white py-4 font-bold text-black uppercase tracking-widest transition-colors hover:bg-pandora-cyan"
          onClick={onProceed}
          type="button"
        >
          {t("checkout.proceedToPayment").toUpperCase()}
          <ChevronRight className="transition-transform group-hover:translate-x-1" size={18} />
        </button>
      </div>
    </motion.div>
  );
};

export default memo(CartSummary);
