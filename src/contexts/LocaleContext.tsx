/**
 * LocaleContext
 * 
 * Manages user's language and currency preferences globally.
 * Updates automatically when user changes preferences in profile.
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import type { ProfileData } from '../types/component';

type LocaleCode = 'en' | 'ru' | 'uk' | 'de' | 'fr' | 'es' | 'tr' | 'ar' | 'hi';
type CurrencyCode = 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED';

interface LocaleContextValue {
  locale: LocaleCode;
  currency: CurrencyCode;
  setLocale: (locale: LocaleCode) => void;
  setCurrency: (currency: CurrencyCode) => void;
  updateFromProfile: (profile: ProfileData | null) => void;
}

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

interface LocaleProviderProps {
  children: ReactNode;
  initialProfile?: ProfileData | null;
}

/**
 * Get default locale from Telegram or browser
 */
function getDefaultLocale(): LocaleCode {
  if (typeof window === 'undefined') return 'en';
  
  const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
  const browserLang = navigator.language?.split('-')[0];
  const detectedLang = tgLang || browserLang || 'en';
  
  const supportedLocales: LocaleCode[] = ['en', 'ru', 'uk', 'de', 'fr', 'es', 'tr', 'ar', 'hi'];
  return (supportedLocales.includes(detectedLang as LocaleCode) ? detectedLang : 'en') as LocaleCode;
}

/**
 * Get default currency based on locale
 */
function getCurrencyForLocale(locale: LocaleCode): CurrencyCode {
  const localeToCurrency: Record<LocaleCode, CurrencyCode> = {
    'ru': 'RUB',
    'uk': 'UAH',
    'en': 'USD',
    'de': 'EUR',
    'fr': 'EUR',
    'es': 'EUR',
    'tr': 'TRY',
    'ar': 'AED',
    'hi': 'INR',
  };
  return localeToCurrency[locale] || 'USD';
}

export function LocaleProvider({ children, initialProfile }: LocaleProviderProps) {
  const defaultLocale = getDefaultLocale();
  const defaultCurrency = getCurrencyForLocale(defaultLocale);
  
  // Initialize from profile if available, otherwise use defaults
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
    }
  }, []);
  
  // Update locale and HTML lang attribute
  const setLocale = useCallback((newLocale: LocaleCode) => {
    setLocaleState(newLocale);
    document.documentElement.lang = newLocale;
    
    // Auto-update currency if not explicitly set by user
    // Only if currency matches the old locale's default
    const oldCurrency = getCurrencyForLocale(locale);
    if (currency === oldCurrency) {
      const newCurrency = getCurrencyForLocale(newLocale);
      setCurrencyState(newCurrency);
    }
  }, [locale, currency]);
  
  const setCurrency = useCallback((newCurrency: CurrencyCode) => {
    setCurrencyState(newCurrency);
  }, []);
  
  // Update HTML lang attribute when locale changes
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  
  const value: LocaleContextValue = {
    locale,
    currency,
    setLocale,
    setCurrency,
    updateFromProfile,
  };
  
  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocaleContext(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (context === undefined) {
    throw new Error('useLocaleContext must be used within LocaleProvider');
  }
  return context;
}

