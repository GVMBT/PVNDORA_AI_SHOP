/**
 * Currency formatting utilities for frontend
 *
 * Simplified for RUB-only system. All amounts are in RUB.
 */

export type CurrencyCode = "RUB";

/**
 * Get currency symbol (always RUB)
 */
export function getCurrencySymbol(_currency: string = "RUB"): string {
  return "₽";
}

/**
 * Format price with RUB symbol
 *
 * @param price - Price value in RUB
 * @param _currency - Ignored (always RUB)
 * @returns Formatted price string like "1,234 ₽"
 *
 * Examples:
 * - formatPrice(1234) => '1,234 ₽'
 * - formatPrice(5000) => '5,000 ₽'
 */
export function formatPrice(price: number, _currency: string = "RUB"): string {
  // RUB is always integer, no decimals
  const formatted = Math.round(price).toLocaleString("ru-RU", { maximumFractionDigits: 0 });
  return `${formatted} ₽`;
}

/**
 * Format price for display (backwards compatible alias)
 */
export function formatRub(price: number): string {
  return formatPrice(price, "RUB");
}
