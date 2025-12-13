/**
 * Cart Adapter
 * 
 * Transforms API cart data into component-friendly format.
 */

import type { APICartResponse, APICartItem } from '../types/api';
import type { CartData, CartItem } from '../types/component';

/**
 * Adapt single cart item
 */
function adaptCartItem(item: APICartItem): CartItem {
  return {
    id: item.product_id,
    name: item.product_name,
    category: 'Module', // Not provided in API
    price: item.unit_price,
    quantity: item.quantity,
    image: `/noise.png`, // No images for cart items, use placeholder
  };
}

/**
 * Adapt API cart response to component format
 */
export function adaptCart(response: APICartResponse): CartData {
  // Response has items at root level, not inside cart
  const items = response.items || [];
  
  return {
    items: items.map(adaptCartItem),
    total: response.total || 0,
    originalTotal: response.subtotal || response.total || 0,
    discountTotal: (response.subtotal || 0) - (response.total || 0),
    promoCode: response.promo_code,
    promoDiscountPercent: response.promo_discount_percent,
  };
}


