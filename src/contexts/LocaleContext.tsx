/**
 * LocaleContext
 *
 * Manages user's language preference globally.
 * Simplified for RUB-only currency system.
 *
 * ARCHITECTURE:
 * - All amounts are in RUB
 * - No currency conversion needed
 * - Language still supports RU/EN for interface
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

// Only RU/EN supported for interface
type LocaleCode = "en" | "ru";

// Only RUB currency (constant)
const CURRENCY = "RUB" as const;
const CURRENCY_SYMBOL = "₽";

interface LocaleContextValue {
  locale: LocaleCode;
  currency: "RUB";
  exchangeRate: 1; // Always 1 (no conversion)
  setLocale: (locale: LocaleCode) => void;
  setCurrency: (currency: string) => void; // No-op for backwards compatibility
  setExchangeRate: (rate: number) => void; // No-op for backwards compatibility
  updateFromProfile: (profile: ProfileData | null) => void;
  // Currency helpers
  convertFromUsd: (amountRub: number) => number; // No-op, returns same value
  formatPrice: (amount: number, currencyOverride?: string) => string;
  formatPriceUsd: (amountRub: number) => string; // Same as formatPrice now
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
  if (globalThis.window === undefined) return "ru";

  const tgLang = globalThis.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
  const browserLang = navigator.language?.split("-")[0];
  const detectedLang = tgLang || browserLang || "ru";

  // Russian-speaking locales map to RU, others to EN
  const russianLocales = ["ru", "be", "uk", "kk"];
  return russianLocales.includes(detectedLang) ? "ru" : "en";
}

export function LocaleProvider({ children, initialProfile }: Readonly<LocaleProviderProps>) {
  const defaultLocale = getDefaultLocale();

  const [locale, setLocaleState] = useState<LocaleCode>(() => {
    if (initialProfile?.interfaceLanguage) {
      return (initialProfile.interfaceLanguage as LocaleCode) || defaultLocale;
    }
    return defaultLocale;
  });

  // Update from profile data
  const updateFromProfile = useCallback((profile: ProfileData | null) => {
    if (profile?.interfaceLanguage) {
      setLocaleState(profile.interfaceLanguage as LocaleCode);
      document.documentElement.lang = profile.interfaceLanguage;
    }
  }, []);

  const setLocale = useCallback((newLocale: LocaleCode) => {
    setLocaleState(newLocale);
    document.documentElement.lang = newLocale;
  }, []);

  // No-op functions for backwards compatibility
  const setCurrency = useCallback((_currency: string) => {
    // Currency is always RUB now
  }, []);

  const setExchangeRate = useCallback((_rate: number) => {
    // Exchange rate is always 1 now
  }, []);

  // No conversion needed - returns same value
  const convertFromUsd = useCallback((amountRub: number): number => {
    return Math.round(amountRub);
  }, []);

  // Format price with RUB symbol
  const formatPrice = useCallback((amount: number, _currencyOverride?: string): string => {
    const formatted = Math.round(amount).toLocaleString("ru-RU", { maximumFractionDigits: 0 });
    return `${formatted} ${CURRENCY_SYMBOL}`;
  }, []);

  // Same as formatPrice now (no USD conversion)
  const formatPriceUsd = useCallback(
    (amountRub: number): string => {
      return formatPrice(amountRub);
    },
    [formatPrice]
  );

  // Update HTML lang attribute
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({
      locale,
      currency: CURRENCY,
      exchangeRate: 1,
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
