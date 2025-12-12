/**
 * Cart Adapter
 * 
 * Transforms API cart data into component-friendly format.
 */

import type { APICart, APICartResponse } from '../types/api';
import type { CartData, CartItem } from '../types/component';

/**
 * Adapt single cart item
 */
function adaptCartItem(item: {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
}): CartItem {
  return {
    id: item.product_id,
    name: item.product_name,
    category: 'Module', // Not provided in API
    price: item.unit_price,
    quantity: item.quantity,
    image: `https://picsum.photos/seed/${item.product_id.substring(0, 8)}/200/200`,
  };
}

/**
 * Adapt API cart response to component format
 */
export function adaptCart(response: APICartResponse): CartData {
  const { cart } = response;
  
  return {
    items: cart.items.map(adaptCartItem),
    total: cart.total,
    originalTotal: cart.original_total,
    discountTotal: cart.discount_total,
    promoCode: cart.promo_code,
    promoDiscountPercent: cart.promo_discount_percent,
  };
}


