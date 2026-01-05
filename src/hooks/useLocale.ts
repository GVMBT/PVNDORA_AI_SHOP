import { useCallback, useMemo } from 'react';
import { useLocaleContext } from '../contexts/LocaleContext';

// Import only RU/EN locale files (only supported languages)
import en from '../../locales/en.json';
import ru from '../../locales/ru.json';

// Only RU/EN supported for now
type LocaleCode = 'en' | 'ru';
type CurrencyCode = 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED' | 'GBP';

const locales: Record<LocaleCode, Record<string, any>> = { en, ru };

interface UseLocaleReturn {
  locale: LocaleCode;
  language: LocaleCode;  // Alias for locale (backwards compatibility)
  setLocale: (locale: LocaleCode) => void;
  currency: CurrencyCode;
  isRTL: boolean;
  t: (key: string, params?: Record<string, string | number>) => string;
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
  const locale: LocaleCode = (contextLocale === 'ru' ? 'ru' : 'en') as LocaleCode;
  
  // RU and EN are both LTR
  const isRTL = false;
  
  const t = useCallback((key: string, params: Record<string, string | number> = {}): string => {
    const keys = key.split('.');
    let value: any = locales[locale];
    
    for (const k of keys) {
      value = value?.[k];
      if (value === undefined) break;
    }
    
    // Fallback to English
    if (value === undefined) {
      value = locales.en;
      for (const k of keys) {
        value = value?.[k];
        if (value === undefined) break;
      }
    }
    
    // Return key if not found
    if (value === undefined) {
      return key;
    }
    
    // Replace params
    if (typeof value === 'string' && Object.keys(params).length > 0) {
      return value.replace(/\{(\w+)\}/g, (_, paramKey) => String(params[paramKey] ?? `{${paramKey}}`));
    }
    
    return value;
  }, [locale]);

  const formatPrice = useCallback((amount: number, currencyOverride: CurrencyCode | null = null): string => {
    // Use provided currency or context currency
    const targetCurrency = currencyOverride || currency;
    
    // Custom formatting for better control
    const symbols: Record<string, string> = {
      'USD': '$',
      'RUB': '₽',
      'EUR': '€',
      'UAH': '₴',
      'TRY': '₺',
      'INR': '₹',
      'AED': 'د.إ'
    };
    
    const symbol = symbols[targetCurrency] || targetCurrency;
    
    // Format number based on currency
    let formatted: string;
    if (['RUB', 'UAH', 'TRY', 'INR'].includes(targetCurrency)) {
      formatted = Math.round(amount).toLocaleString(locale);
    } else {
      formatted = amount.toLocaleString(locale, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      });
    }
    
    // Place symbol based on currency
    if (['USD', 'EUR', 'GBP'].includes(targetCurrency)) {
      return `${symbol}${formatted}`;
    } else {
      return `${formatted} ${symbol}`;
    }
  }, [locale, currency]);
  
  const formatDate = useCallback((date: string | Date, options: Intl.DateTimeFormatOptions = {}): string => {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      ...options
    }).format(new Date(date));
  }, [locale]);
  
  return {
    locale,
    language: locale,  // Alias for locale (backwards compatibility)
    setLocale: setLocaleContext,
    currency,
    isRTL,
    t,
    formatPrice,
    formatDate
  };
}

export default useLocale;
