import { useCallback } from "react";
// Import only RU/EN locale files (only supported languages)
import en from "../../locales/en.json";
import ru from "../../locales/ru.json";
import { useLocaleContext } from "../contexts/LocaleContext";

// Only RU/EN supported for now
type LocaleCode = "en" | "ru";
type CurrencyCode = "USD" | "RUB" | "EUR" | "UAH" | "TRY" | "INR" | "AED" | "GBP";

type LocaleValue = string | LocaleObject;
interface LocaleObject {
  [key: string]: LocaleValue;
}
const locales: Record<LocaleCode, LocaleObject> = { en, ru };

interface UseLocaleReturn {
  locale: LocaleCode;
  language: LocaleCode; // Alias for locale (backwards compatibility)
  setLocale: (locale: LocaleCode) => void;
  currency: CurrencyCode;
  isRTL: boolean;
  t: (key: string, params?: Record<string, string | number>) => string;
  /** Always resolve from English locale. Use for page titles that stay in English (e.g. LEADERBOARD: TOP_SAVINGS) on any UI language. */
  tEn: (key: string, params?: Record<string, string | number>) => string;
  formatPrice: (amount: number, currency?: CurrencyCode | null) => string;
  formatDate: (date: string | Date, options?: Intl.DateTimeFormatOptions) => string;
}

/**
 * Hook for localization
 * Only supports RU/EN languages
 */
export function useLocale(): UseLocaleReturn {
  const { locale: contextLocale, currency, setLocale: setLocaleContext } = useLocaleContext();

  // Ensure locale is always RU or EN (normalize any other value)
  const locale: LocaleCode = (contextLocale === "ru" ? "ru" : "en") as LocaleCode;

  // RU and EN are both LTR
  const isRTL = false;

  const t = useCallback(
    (key: string, params: Record<string, string | number> = {}): string => {
      // Helper functions for locale translation (reduce cognitive complexity)
      const resolveLocaleValue = (
        localeObj: LocaleObject,
        keysArray: string[]
      ): LocaleValue | undefined => {
        let value: LocaleValue | undefined = localeObj;
        for (const k of keysArray) {
          if (value && typeof value === "object" && k in value) {
            value = value[k];
          } else {
            return undefined;
          }
        }
        return value;
      };

      const replaceParams = (text: string, paramsObj: Record<string, string | number>): string => {
        if (Object.keys(paramsObj).length === 0) return text;
        return text.replaceAll(/\{(\w+)\}/g, (_: string, paramKey: string) =>
          String(paramsObj[paramKey] ?? `{${paramKey}}`)
        );
      };

      const keys = key.split(".");

      // Try current locale first
      let value = resolveLocaleValue(locales[locale], keys);

      // Fallback to English if not found
      if (value === undefined) {
        value = resolveLocaleValue(locales.en, keys);
      }

      // Return key if not found
      if (value === undefined) {
        return key;
      }

      // Ensure we return a string
      if (typeof value === "string") {
        return replaceParams(value, params);
      }

      // If value is an object, return the key as fallback
      return key;
    },
    [locale]
  );

  const tEn = useCallback(
    (key: string, params: Record<string, string | number> = {}): string => {
      const resolveLocaleValue = (
        localeObj: LocaleObject,
        keysArray: string[]
      ): LocaleValue | undefined => {
        let value: LocaleValue | undefined = localeObj;
        for (const k of keysArray) {
          if (value && typeof value === "object" && k in value) {
            value = value[k];
          } else {
            return undefined;
          }
        }
        return value;
      };
      const replaceParams = (text: string, paramsObj: Record<string, string | number>): string => {
        if (Object.keys(paramsObj).length === 0) return text;
        return text.replaceAll(/\{(\w+)\}/g, (_: string, paramKey: string) =>
          String(paramsObj[paramKey] ?? `{${paramKey}}`)
        );
      };
      const keys = key.split(".");
      const value = resolveLocaleValue(locales.en, keys);
      if (value === undefined) return key;
      if (typeof value === "string") return replaceParams(value, params);
      return key;
    },
    []
  );

  const formatPrice = useCallback(
    (amount: number, currencyOverride: CurrencyCode | null = null): string => {
      // Use provided currency or context currency
      const targetCurrency = currencyOverride || currency;

      // Custom formatting for better control
      const symbols: Record<string, string> = {
        USD: "$",
        RUB: "₽",
        EUR: "€",
        UAH: "₴",
        TRY: "₺",
        INR: "₹",
        AED: "د.إ",
      };

      const symbol = symbols[targetCurrency] || targetCurrency;

      // Format number based on currency
      let formatted: string;
      if (["RUB", "UAH", "TRY", "INR"].includes(targetCurrency)) {
        formatted = Math.round(amount).toLocaleString(locale);
      } else {
        formatted = amount.toLocaleString(locale, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      }

      // Place symbol based on currency
      if (["USD", "EUR", "GBP"].includes(targetCurrency)) {
        return `${symbol}${formatted}`;
      } else {
        return `${formatted} ${symbol}`;
      }
    },
    [locale, currency]
  );

  const formatDate = useCallback(
    (date: string | Date, options: Intl.DateTimeFormatOptions = {}): string => {
      return new Intl.DateTimeFormat(locale, {
        dateStyle: "medium",
        ...options,
      }).format(new Date(date));
    },
    [locale]
  );

  return {
    locale,
    language: locale, // Alias for locale (backwards compatibility)
    setLocale: setLocaleContext,
    currency,
    isRTL,
    t,
    tEn,
    formatPrice,
    formatDate,
  };
}

export default useLocale;
