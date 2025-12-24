/**
 * Cart Data Converter
 * 
 * Utility functions for converting between different cart data formats.
 * Used to bridge legacy Cart interface with modern CartData type.
 */

import type { CartData, CartItem as ComponentCartItem } from '../types/component';

/**
 * Legacy Cart interface (used in useCheckoutFlow)
 */
export interface LegacyCartItem {
  product_id: string;
  quantity: number;
  product?: {
    id: string;
    name: string;
    price: number;
    final_price?: number;
    currency?: string;
  };
  [key: string]: unknown;
}

export interface LegacyCart {
  items: LegacyCartItem[];
  total?: number;
  subtotal?: number;
  promo_code?: string;
  promo_discount_percent?: number;
  currency?: string;
}

/**
 * Convert CartData (from CartContext) to legacy Cart format
 * Used for backward compatibility with useCheckoutFlow
 * 
 * @param cartData - Modern CartData from CartContext
 * @returns Legacy Cart format or null if cart is empty
 * 
 * @example
 * ```ts
 * const legacyCart = convertCartDataToLegacyCart(cartData);
 * // { items: [...], total: 100, subtotal: 100, ... }
 * ```
 */
export function convertCartDataToLegacyCart(cartData: CartData | null): LegacyCart | null {
  if (!cartData || !cartData.items || cartData.items.length === 0) {
    return null;
  }

  return {
    items: cartData.items.map((item: ComponentCartItem) => ({
      product_id: item.id,
      quantity: item.quantity,
      product: {
        id: item.id,
        name: item.name,
        price: item.price,
        final_price: item.price, // Use price as final_price if not available
        currency: item.currency,
      },
    })),
    total: cartData.total,
    subtotal: cartData.originalTotal || cartData.total,
    promo_code: cartData.promoCode,
    promo_discount_percent: cartData.promoDiscountPercent,
    currency: cartData.currency,
  };
}

/**
 * Get subtotal from CartData (original total before discounts)
 * 
 * @param cartData - CartData from CartContext
 * @returns Subtotal amount or 0 if cart is empty
 */
export function getCartSubtotal(cartData: CartData | null): number {
  if (!cartData) return 0;
  return cartData.originalTotal || cartData.total || 0;
}

/**
 * Get total from CartData (with promo discount applied)
 * 
 * @param cartData - CartData from CartContext
 * @returns Total amount after discounts or 0 if cart is empty
 */
export function getCartTotal(cartData: CartData | null): number {
  if (!cartData) return 0;
  return cartData.total || 0;
}


































