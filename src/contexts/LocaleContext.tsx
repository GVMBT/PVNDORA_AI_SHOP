/**
 * LocaleContext
 *
 * Manages user's language and currency preferences globally.
 * Provides unified currency conversion functions.
 *
 * ARCHITECTURE:
 * - All amounts from API include both USD and display values
 * - exchangeRate is stored for fallback conversion
 * - Use USD values for all calculations/comparisons
 * - Use display values or convertFromUsd() for UI
 */

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ProfileData } from "../types/component";

// Only RU/EN supported for now (can be extended later)
type LocaleCode = "en" | "ru";
type CurrencyCode = "USD" | "RUB" | "EUR" | "UAH" | "TRY" | "INR" | "AED" | "GBP";

// Currency symbols
const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  RUB: "₽",
  EUR: "€",
  UAH: "₴",
  TRY: "₺",
  INR: "₹",
  AED: "د.إ",
  GBP: "£",
};

// Currencies displayed as integers (no decimals)
const INTEGER_CURRENCIES = new Set(["RUB", "UAH", "TRY", "INR", "JPY", "KRW"]);

interface LocaleContextValue {
  locale: LocaleCode;
  currency: CurrencyCode;
  exchangeRate: number; // 1 USD = X currency
  setLocale: (locale: LocaleCode) => void;
  setCurrency: (currency: CurrencyCode) => void;
  setExchangeRate: (rate: number) => void;
  updateFromProfile: (profile: ProfileData | null) => void;
  // Currency helpers
  convertFromUsd: (amountUsd: number) => number;
  formatPrice: (amount: number, currencyOverride?: string) => string;
  formatPriceUsd: (amountUsd: number) => string;
}

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

interface LocaleProviderProps {
  children: ReactNode;
  initialProfile?: ProfileData | null;
}

/**
 * Get default locale from Telegram or browser
 * Only supports RU/EN - Russian-speaking users get RU, others get EN
 */
function getDefaultLocale(): LocaleCode {
  if (globalThis.window === undefined) return "en";

  const tgLang = globalThis.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
  const browserLang = navigator.language?.split("-")[0];
  const detectedLang = tgLang || browserLang || "en";

  // Only RU or EN supported - Russian-speaking locales map to RU, others to EN
  const russianLocales = ["ru", "be", "uk", "kk"]; // Russian, Belarusian, Ukrainian, Kazakh
  return russianLocales.includes(detectedLang) ? "ru" : "en";
}

/**
 * Get default currency based on locale
 * Only RU/EN supported - RU users get RUB, EN users get USD
 */
function getCurrencyForLocale(locale: LocaleCode): CurrencyCode {
  const localeToCurrency: Record<LocaleCode, CurrencyCode> = {
    ru: "RUB",
    en: "USD",
  };
  return localeToCurrency[locale] || "USD";
}

export function LocaleProvider({ children, initialProfile }: Readonly<LocaleProviderProps>) {
  const defaultLocale = getDefaultLocale();
  const defaultCurrency = getCurrencyForLocale(defaultLocale);

  const [locale, setLocaleState] = useState<LocaleCode>(() => {
    if (initialProfile?.interfaceLanguage) {
      return (initialProfile.interfaceLanguage as LocaleCode) || defaultLocale;
    }
    return defaultLocale;
  });

  const [currency, setCurrencyState] = useState<CurrencyCode>(() => {
    if (initialProfile?.currency) {
      return (initialProfile.currency as CurrencyCode) || defaultCurrency;
    }
    return defaultCurrency;
  });

  const [exchangeRate, setExchangeRateState] = useState<number>(() => {
    return initialProfile?.exchangeRate || 1;
  });

  // Update from profile data
  const updateFromProfile = useCallback((profile: ProfileData | null) => {
    if (profile) {
      if (profile.interfaceLanguage) {
        setLocaleState(profile.interfaceLanguage as LocaleCode);
        document.documentElement.lang = profile.interfaceLanguage;
      }
      if (profile.currency) {
        setCurrencyState(profile.currency as CurrencyCode);
      }
      if (profile.exchangeRate !== undefined) {
        setExchangeRateState(profile.exchangeRate);
      }
    }
  }, []);

  const setLocale = useCallback(
    (newLocale: LocaleCode) => {
      setLocaleState(newLocale);
      document.documentElement.lang = newLocale;

      const oldCurrency = getCurrencyForLocale(locale);
      if (currency === oldCurrency) {
        const newCurrency = getCurrencyForLocale(newLocale);
        setCurrencyState(newCurrency);
      }
    },
    [locale, currency]
  );

  const setCurrency = useCallback((newCurrency: CurrencyCode) => {
    setCurrencyState(newCurrency);
  }, []);

  const setExchangeRate = useCallback((rate: number) => {
    setExchangeRateState(rate);
  }, []);

  // Convert USD amount to display currency
  const convertFromUsd = useCallback(
    (amountUsd: number): number => {
      if (currency === "USD" || exchangeRate === 1) {
        return amountUsd;
      }
      const converted = amountUsd * exchangeRate;
      // Round integer currencies
      if (INTEGER_CURRENCIES.has(currency)) {
        return Math.round(converted);
      }
      return Math.round(converted * 100) / 100;
    },
    [currency, exchangeRate]
  );

  // Format price with currency symbol
  const formatPrice = useCallback(
    (amount: number, currencyOverride?: string): string => {
      const curr = currencyOverride || currency;
      const symbol = CURRENCY_SYMBOLS[curr] || curr;

      let formatted: string;
      if (INTEGER_CURRENCIES.has(curr)) {
        formatted = Math.round(amount).toLocaleString("en-US", { maximumFractionDigits: 0 });
      } else {
        formatted = amount.toLocaleString("en-US", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
      }

      // Symbol placement
      if (["USD", "EUR", "GBP"].includes(curr)) {
        return `${symbol}${formatted}`;
      }
      return `${formatted} ${symbol}`;
    },
    [currency]
  );

  // Format USD amount in user's currency
  const formatPriceUsd = useCallback(
    (amountUsd: number): string => {
      const displayAmount = convertFromUsd(amountUsd);
      return formatPrice(displayAmount);
    },
    [convertFromUsd, formatPrice]
  );

  // Update HTML lang attribute
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      currency,
      exchangeRate,
      setLocale,
      setCurrency,
      setExchangeRate,
      updateFromProfile,
      convertFromUsd,
      formatPrice,
      formatPriceUsd,
    }),
    [
      locale,
      currency,
      exchangeRate,
      setLocale,
      setCurrency,
      setExchangeRate,
      updateFromProfile,
      convertFromUsd,
      formatPrice,
      formatPriceUsd,
    ]
  );

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocaleContext(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (context === undefined) {
    throw new Error("useLocaleContext must be used within LocaleProvider");
  }
  return context;
}
