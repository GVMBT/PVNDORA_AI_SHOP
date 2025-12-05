import { useState, useEffect, useCallback, useMemo } from 'react'

// Import all locale files
import en from '../../locales/en.json'
import ru from '../../locales/ru.json'
import uk from '../../locales/uk.json'
import de from '../../locales/de.json'
import fr from '../../locales/fr.json'
import es from '../../locales/es.json'
import tr from '../../locales/tr.json'
import ar from '../../locales/ar.json'
import hi from '../../locales/hi.json'

const locales = { en, ru, uk, de, fr, es, tr, ar, hi }

const RTL_LANGUAGES = ['ar', 'he', 'fa']

/**
 * Hook for localization
 */
export function useLocale() {
  const [locale, setLocale] = useState('en')
  
  useEffect(() => {
    // Get language from Telegram or browser
    const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
    const browserLang = navigator.language?.split('-')[0]
    
    const detectedLang = tgLang || browserLang || 'en'
    const supportedLang = locales[detectedLang] ? detectedLang : 'en'
    
    setLocale(supportedLang)
    
    // Set HTML lang attribute
    document.documentElement.lang = supportedLang
  }, [])
  
  const isRTL = useMemo(() => RTL_LANGUAGES.includes(locale), [locale])
  
  const t = useCallback((key, params = {}) => {
    const keys = key.split('.')
    let value = locales[locale]
    
    for (const k of keys) {
      value = value?.[k]
      if (value === undefined) break
    }
    
    // Fallback to English
    if (value === undefined) {
      value = locales.en
      for (const k of keys) {
        value = value?.[k]
        if (value === undefined) break
      }
    }
    
    // Return key if not found
    if (value === undefined) {
      return key
    }
    
    // Replace params
    if (typeof value === 'string' && Object.keys(params).length > 0) {
      return value.replace(/\{(\w+)\}/g, (_, key) => params[key] ?? `{${key}}`)
    }
    
    return value
  }, [locale])
  
  // Determine currency based on language
  const getCurrency = useCallback(() => {
    const languageToCurrency = {
      'ru': 'RUB',
      'uk': 'UAH',
      'en': 'USD',
      'de': 'EUR',
      'fr': 'EUR',
      'es': 'EUR',
      'tr': 'TRY',
      'ar': 'AED',
      'hi': 'INR',
      'be': 'RUB',
      'kk': 'RUB'
    }
    return languageToCurrency[locale] || 'USD'
  }, [locale])

  const formatPrice = useCallback((amount, currency = null) => {
    // Use provided currency or determine from language
    const targetCurrency = currency || getCurrency()
    
    // Custom formatting for better control
    const symbols = {
      'USD': '$',
      'RUB': '₽',
      'EUR': '€',
      'UAH': '₴',
      'TRY': '₺',
      'INR': '₹',
      'AED': 'د.إ'
    }
    
    const symbol = symbols[targetCurrency] || targetCurrency
    
    // Format number based on currency
    let formatted
    if (['RUB', 'UAH', 'TRY', 'INR'].includes(targetCurrency)) {
      formatted = Math.round(amount).toLocaleString(locale)
    } else {
      formatted = amount.toLocaleString(locale, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      })
    }
    
    // Place symbol based on currency
    if (['USD', 'EUR', 'GBP'].includes(targetCurrency)) {
      return `${symbol}${formatted}`
    } else {
      return `${formatted} ${symbol}`
    }
  }, [locale, getCurrency])
  
  const formatDate = useCallback((date, options = {}) => {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      ...options
    }).format(new Date(date))
  }, [locale])
  
  return {
    locale,
    setLocale,
    isRTL,
    t,
    formatPrice,
    formatDate
  }
}

export default useLocale




