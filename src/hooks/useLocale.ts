import { useCallback, useMemo } from 'react';
import { useLocaleContext } from '../contexts/LocaleContext';

// Import all locale files
import en from '../../locales/en.json';
import ru from '../../locales/ru.json';
import uk from '../../locales/uk.json';
import de from '../../locales/de.json';
import fr from '../../locales/fr.json';
import es from '../../locales/es.json';
import tr from '../../locales/tr.json';
import ar from '../../locales/ar.json';
import hi from '../../locales/hi.json';

type LocaleCode = 'en' | 'ru' | 'uk' | 'de' | 'fr' | 'es' | 'tr' | 'ar' | 'hi';
type CurrencyCode = 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED';

const locales: Record<LocaleCode, Record<string, any>> = { en, ru, uk, de, fr, es, tr, ar, hi };
const RTL_LANGUAGES: string[] = ['ar', 'he', 'fa'];

interface UseLocaleReturn {
  locale: LocaleCode;
  setLocale: (locale: LocaleCode) => void;
  currency: CurrencyCode;
  isRTL: boolean;
  t: (key: string, params?: Record<string, string | number>) => string;
  formatPrice: (amount: number, currency?: CurrencyCode | null) => string;
  formatDate: (date: string | Date, options?: Intl.DateTimeFormatOptions) => string;
}

/**
 * Hook for localization
 * Now uses LocaleContext for global state management
 */
export function useLocale(): UseLocaleReturn {
  const { locale, currency, setLocale: setLocaleContext } = useLocaleContext();
  
  const isRTL = useMemo(() => RTL_LANGUAGES.includes(locale), [locale]);
  
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
    setLocale: setLocaleContext,
    currency,
    isRTL,
    t,
    formatPrice,
    formatDate
  };
}

export default useLocale;
