/**
 * Cart Adapter
 *
 * Transforms API cart data into component-friendly format.
 *
 * UNIFIED CURRENCY ARCHITECTURE:
 * - API returns both *_usd (for calculations) and display values (for UI)
 * - Always use _usd values for comparisons
 * - Use display values or formatPrice for UI
 */

import type { APICartItem, APICartResponse } from "../types/api";
import type { CartData, CartItem } from "../types/component";

/**
 * Adapt single cart item
 */
function adaptCartItem(item: APICartItem, currency: string): CartItem {
  return {
    id: item.product_id,
    name: item.product_name,
    category: "Module",
    // Display price (in user's currency)
    price: item.unit_price || item.final_price || 0,
    // USD price (for calculations)
    priceUsd: item.unit_price_usd || item.final_price_usd || item.unit_price || 0,
    currency: item.currency || currency,
    quantity: item.quantity,
    image: item.image_url || "/noise.png",
  };
}

/**
 * Adapt API cart response to component format
 */
export function adaptCart(response: APICartResponse): CartData {
  const items = response.items || [];
  const currency = response.currency || "USD";
  const exchangeRate = response.exchange_rate || 1;

  // USD values (for calculations) - ALWAYS use these for math
  const totalUsd = response.total_usd ?? response.total ?? 0;
  const originalTotalUsd = response.original_total_usd ?? response.subtotal_usd ?? totalUsd;

  // Display values (for UI)
  const total = response.total ?? 0;
  const originalTotal = response.original_total ?? response.subtotal ?? total;

  return {
    items: items.map((item) => adaptCartItem(item, currency)),
    // Display values (for UI)
    total,
    originalTotal,
    discountTotal: originalTotal - total,
    // USD values (for calculations)
    totalUsd,
    originalTotalUsd,
    discountTotalUsd: originalTotalUsd - totalUsd,
    // Currency info
    currency,
    exchangeRate,
    // Promo
    promoCode: response.promo_code,
    promoDiscountPercent: response.promo_discount_percent,
  };
}
