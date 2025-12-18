/**
 * ProfileConnected
 * 
 * Connected version of Profile component with real API data.
 */

import React, { useEffect, useState, useCallback, useMemo } from 'react';
import Profile from './Profile';
import { useProfileTyped } from '../../hooks/useApiTyped';
import { useTelegram } from '../../hooks/useTelegram';
import { useCyberModal } from './CyberModal';
import { useClipboard } from '../../hooks/useClipboard';
import { useLocaleContext } from '../../contexts/LocaleContext';
import { useCart } from '../../contexts/CartContext';
import { logger } from '../../utils/logger';
import type { ProfileData } from '../../types/component';

interface ProfileConnectedProps {
  onBack: () => void;
  onHaptic?: (type?: 'light' | 'medium') => void;
  onAdminEnter?: () => void;
}

const ProfileConnected: React.FC<ProfileConnectedProps> = ({
  onBack,
  onHaptic,
  onAdminEnter,
}) => {
  const { profile, getProfile, requestWithdrawal, createShareLink, createTopUp, updatePreferences, loading, error } = useProfileTyped();
  const { hapticFeedback, showConfirm, openLink, showAlert: showTelegramAlert } = useTelegram();
  const { showTopUp, showWithdraw, showAlert: showModalAlert } = useCyberModal();
  const { updateFromProfile, setCurrency, setLocale, currency: contextCurrency } = useLocaleContext();
  const { clearCartState } = useCart();
  const [isInitialized, setIsInitialized] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const { copy: copyToClipboard } = useClipboard();

  // Initial load
  useEffect(() => {
    const init = async () => {
      const fetchedProfile = await getProfile();
      if (fetchedProfile) {
        // Initialize context from profile only on first load
        updateFromProfile(fetchedProfile);
      }
      setIsInitialized(true);
    };
    init();
  }, [getProfile, updateFromProfile]);          

  // Auto-refresh profile when page becomes visible (handles returning from Telegram notifications)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isInitialized) {
        // Refresh profile when user returns to the page (might have received level up notification)
        getProfile();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [isInitialized, getProfile]);          

  const handleCopyLink = useCallback(async () => {
    if (!profile?.referralLink) return;
    if (onHaptic) onHaptic('light');
    
    const success = await copyToClipboard(profile.referralLink);
    if (success) {
      hapticFeedback?.('notification', 'success');
      showTelegramAlert('Ссылка скопирована!');
    }
  }, [profile?.referralLink, onHaptic, hapticFeedback, showTelegramAlert, copyToClipboard]);

  const handleShare = useCallback(async () => {
    setShareLoading(true);
    if (onHaptic) onHaptic('medium');
    
    try {
      const { prepared_message_id } = await createShareLink();
      
      // Try Telegram's shareMessage first
      const tgWebApp = window.Telegram?.WebApp;
      if (tgWebApp?.shareMessage) {
        tgWebApp.shareMessage(prepared_message_id, () => {
          // Share completed
        });
      } else if (tgWebApp?.switchInlineQuery) {
        tgWebApp.switchInlineQuery('invite', ['users', 'groups', 'channels']);
      } else {
        // Fallback to copy
        await handleCopyLink();
      }
    } catch (err) {
      logger.error('Failed to share', err);
      await handleCopyLink();
    } finally {
      setShareLoading(false);
    }
  }, [onHaptic, createShareLink, handleCopyLink]);

  const handleWithdraw = useCallback(() => {
    const currency = profile?.currency || 'RUB';
    const balance = profile?.balance || 0;
    // Minimum withdrawal is always 10 USD (convert to user's currency)
    const minAmountUSD = 10;
    const exchangeRate = profile?.exchangeRate || 100; // Default: 1 USD = 100 RUB
    const minAmount = currency === 'USD' ? minAmountUSD : minAmountUSD * exchangeRate;
    
    if (balance < minAmount) {
        const minDisplay = currency === 'USD' ? '$10' : `${minAmount.toLocaleString()} ${currency}`;
        showModalAlert('INSUFFICIENT FUNDS', `Minimum withdrawal is ${minDisplay}`, 'warning');
      return;
    }
    
    if (onHaptic) onHaptic('medium');
    
    showWithdraw({
      currency,
      balance,
      minAmount,
      onConfirm: async (amount: number, method: string, details: string) => {
        await requestWithdrawal(amount, method, details);
        hapticFeedback?.('notification', 'success');
        showModalAlert('REQUEST SUBMITTED', 'Your withdrawal request has been submitted. We will process it within 24-48 hours.', 'success');
        await getProfile();
      },
    });
  }, [profile?.balance, profile?.currency, requestWithdrawal, getProfile, hapticFeedback, showWithdraw, showModalAlert, onHaptic]);

  const handleTopUp = useCallback(() => {
    const tgWebApp = window.Telegram?.WebApp;
    // КРИТИЧНО: Используем ОРИГИНАЛЬНУЮ валюту из БД (profile.currency)
    // convertedProfile НЕ должен перезаписывать currency, но на всякий случай используем исходный profile
    const currency = profile?.currency || contextCurrency || 'USD';
    const balance = profile?.balance || 0;
    
    // Minimum top-up amounts (equivalent to ~5 USD)
    const MIN_AMOUNTS: Record<string, number> = {
      'USD': 5,
      'RUB': 500,
      'EUR': 5,
      'UAH': 200,
      'TRY': 150,
      'INR': 400,
      'AED': 20,
    };
    const minAmount = MIN_AMOUNTS[currency] || 5;
    
    if (onHaptic) onHaptic('light');
    
    showTopUp({
      currency,
      balance,
      minAmount,
      onConfirm: async (amount: number) => {
        const result = await createTopUp(amount, currency);
        
        if (result.payment_url) {
          // Replace current window with payment URL
          // After payment, user will be redirected to /payment/result
          window.location.href = result.payment_url;
        }
      },
    });
  }, [contextCurrency, profile?.currency, profile?.balance, createTopUp, showTopUp, onHaptic]);

  // Helper function to convert USD to target currency
  const convertUsdToCurrency = useCallback((amountUsd: number, targetCurrency: string, exchangeRate: number): number => {
    if (targetCurrency === 'USD' || !exchangeRate || exchangeRate === 1.0) {
      return amountUsd;
    }
    // Round to integer for RUB, UAH, TRY, INR; keep 2 decimals for others
    const converted = amountUsd * exchangeRate;
    if (['RUB', 'UAH', 'TRY', 'INR'].includes(targetCurrency)) {
      return Math.round(converted);
    }
    return Math.round(converted * 100) / 100;
  }, []);

  // CRITICAL: All hooks must be called BEFORE any conditional returns
  const handleUpdatePreferences = useCallback(async (preferred_currency?: string, interface_language?: string) => {
    // Optimistic update: change context IMMEDIATELY (UI updates right away)
    if (preferred_currency) {
      setCurrency(preferred_currency as 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED');
      // Clear cart cache when currency changes - cart will be re-fetched with new currency
      clearCartState();
    }
    if (interface_language) {
      // Only RU/EN supported - normalize to these
      const normalizedLang = interface_language === 'ru' ? 'ru' : 'en';
      setLocale(normalizedLang as 'en' | 'ru');
    }
    
    try {
      // Update preferences via API (in background)
      const result = await updatePreferences(preferred_currency, interface_language);
      
      // Always reload profile when currency changes to get correct exchange_rate for new currency
      if (preferred_currency && preferred_currency !== profile?.currency) {
        const updatedProfile = await getProfile(); // Reload to get exchange_rate for new currency
        // Синхронизируем контекст с обновленным профилем
        if (updatedProfile) {
          updateFromProfile(updatedProfile);
        }
      }
      
      return result;
    } catch (error) {
      // Rollback on error: restore previous currency/language from profile
      if (profile) {
        if (preferred_currency) {
          setCurrency(profile.currency as 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED');
        }
        if (interface_language) {
          // Only RU/EN supported
          const originalLang = profile.language === 'ru' ? 'ru' : 'en';
          setLocale(originalLang as 'en' | 'ru');
        }
      }
      throw error;
    }
  }, [updatePreferences, setCurrency, setLocale, getProfile, profile, updateFromProfile, clearCartState]);

  // Convert profile balance to current currency (for display)
  // IMPORTANT: turnover_usd and thresholds are ALWAYS in USD from API, so we must convert them
  const convertedProfile = useMemo(() => {
    if (!profile) return null;
    
    const currentCurrency = contextCurrency || profile.currency;
    const exchangeRate = profile.exchangeRate || 1.0;
    
    // If currency is USD, no conversion needed (but still convert if contextCurrency differs)
    if (currentCurrency === 'USD') {
      // For USD, turnover and thresholds are already in USD, no conversion needed
      return {
        ...profile,
        // НЕ перезаписываем currency - оставляем оригинальный из БД
        // currency: currentCurrency,  // УДАЛЕНО
      };
    }
    
    // If currencies don't match AND exchangeRate is 1.0 (not loaded for new currency),
    // wait for profile to update with correct exchangeRate
    if (currentCurrency !== profile.currency && currentCurrency !== 'USD' && exchangeRate === 1.0) {
      // Exchange rate not yet loaded for new currency, use profile as-is
      return profile;
    }
    
    // Always convert USD amounts (turnover_usd and thresholds are always in USD)
    const convertedTurnover = convertUsdToCurrency(profile.career.currentTurnover, currentCurrency, exchangeRate);
    const convertedMaxTurnover = profile.career.nextLevel 
      ? convertUsdToCurrency(profile.career.nextLevel.min, currentCurrency, exchangeRate)
      : profile.career.currentLevel.max === Infinity 
        ? Infinity 
        : convertUsdToCurrency(profile.career.currentLevel.max, currentCurrency, exchangeRate);
    
    return {
      ...profile,
      balance: convertUsdToCurrency(profile.balanceUsd || profile.balance, currentCurrency, exchangeRate),
      earnedRef: convertUsdToCurrency(profile.earnedRefUsd || profile.earnedRef, currentCurrency, exchangeRate),
      saved: convertUsdToCurrency(profile.savedUsd || profile.saved, currentCurrency, exchangeRate),
      // НЕ перезаписываем currency - оставляем оригинальный из БД для платежей
      // currency: currentCurrency,  // УДАЛЕНО - используем оригинальный profile.currency
      career: {
        ...profile.career,
        currentTurnover: convertedTurnover,
        currentLevel: {
          ...profile.career.currentLevel,
          min: convertUsdToCurrency(profile.career.currentLevel.min, currentCurrency, exchangeRate),
          max: profile.career.currentLevel.max === Infinity ? Infinity : convertUsdToCurrency(profile.career.currentLevel.max, currentCurrency, exchangeRate),
        },
        nextLevel: profile.career.nextLevel ? {
          ...profile.career.nextLevel,
          min: convertUsdToCurrency(profile.career.nextLevel.min, currentCurrency, exchangeRate),
          max: profile.career.nextLevel.max === Infinity ? Infinity : convertUsdToCurrency(profile.career.nextLevel.max, currentCurrency, exchangeRate),
        } : undefined,
      },
    };
  }, [profile, contextCurrency, convertUsdToCurrency]);

  // Loading state
  if (!isInitialized || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Loading Profile...
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !profile) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠</div>
          <div className="font-mono text-sm text-red-400 mb-2">PROFILE_ERROR</div>
          <p className="text-gray-500 text-sm">{error || 'Failed to load profile'}</p>
          <button
            onClick={() => getProfile()}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <Profile
        profile={convertedProfile || profile}
        onBack={onBack}
        onHaptic={onHaptic}
        onAdminEnter={onAdminEnter}
        onCopyLink={handleCopyLink}
        onShare={handleShare}
        shareLoading={shareLoading}
        onWithdraw={handleWithdraw}
        onTopUp={handleTopUp}
        onUpdatePreferences={handleUpdatePreferences}
      />
  );
};

export default ProfileConnected;
