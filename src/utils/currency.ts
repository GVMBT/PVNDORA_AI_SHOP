/**
 * Currency formatting utilities for frontend
 */

export type CurrencyCode = "USD" | "RUB" | "EUR" | "UAH" | "TRY" | "INR" | "AED" | "GBP";

/**
 * Get currency symbol for a currency code
 */
export function getCurrencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    USD: "$",
    RUB: "₽",
    EUR: "€",
    UAH: "₴",
    TRY: "₺",
    INR: "₹",
    AED: "د.إ",
    GBP: "£",
  };

  return symbols[currency.toUpperCase()] || currency.toUpperCase();
}

/**
 * Format price with currency symbol
 *
 * @param price - Price value (number)
 * @param currency - Currency code (USD, RUB, etc.)
 * @returns Formatted price string
 *
 * Examples:
 * - formatPrice(100, 'USD') => '$100.00'
 * - formatPrice(5000, 'RUB') => '5,000 ₽'
 * - formatPrice(50.5, 'EUR') => '€50.50'
 */
export function formatPrice(price: number, currency: string = "USD"): string {
  const symbol = getCurrencySymbol(currency);
  const currencyUpper = currency.toUpperCase();

  // Integer currencies (no decimals)
  const integerCurrencies = ["RUB", "UAH", "TRY", "INR"];
  const isInteger = integerCurrencies.includes(currencyUpper);

  // Format number
  const formatted = isInteger
    ? Math.round(price).toLocaleString("en-US", { maximumFractionDigits: 0 })
    : price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // Symbol placement: USD/EUR/GBP before, others after
  const symbolBefore = ["USD", "EUR", "GBP"].includes(currencyUpper);

  return symbolBefore ? `${symbol}${formatted}` : `${formatted} ${symbol}`;
}
