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
import { useLocale } from '../../hooks/useLocale';
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
  const { t } = useLocale();
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

  // Helper function to convert USD to target currency
  // MUST be defined FIRST - used by convertedProfile
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

  // Convert profile balance to current currency (for display)
  // MUST be defined BEFORE callbacks that use it (handleWithdraw, handleTopUp)
  const convertedProfile = useMemo(() => {
    if (!profile) return null;
    
    const displayCurrency = contextCurrency || profile.currency || 'USD';
    const exchangeRate = profile.exchangeRate || 1.0;
    
    // If currency is USD, use USD values directly
    if (displayCurrency === 'USD') {
      return {
        ...profile,
        currency: displayCurrency,
        balance: profile.balanceUsd || profile.balance,
        earnedRef: profile.earnedRefUsd || profile.earnedRef,
        saved: profile.savedUsd || profile.saved,
      };
    }
    
    // Convert all USD amounts to display currency
    const convertedBalance = convertUsdToCurrency(profile.balanceUsd || profile.balance, displayCurrency, exchangeRate);
    const convertedEarnedRef = convertUsdToCurrency(profile.earnedRefUsd || profile.earnedRef, displayCurrency, exchangeRate);
    const convertedSaved = convertUsdToCurrency(profile.savedUsd || profile.saved, displayCurrency, exchangeRate);
    const convertedTurnover = convertUsdToCurrency(profile.career.currentTurnover, displayCurrency, exchangeRate);
    
    return {
      ...profile,
      currency: displayCurrency,
      balance: convertedBalance,
      earnedRef: convertedEarnedRef,
      saved: convertedSaved,
      career: {
        ...profile.career,
        currentTurnover: convertedTurnover,
        currentLevel: {
          ...profile.career.currentLevel,
          min: convertUsdToCurrency(profile.career.currentLevel.min, displayCurrency, exchangeRate),
          max: profile.career.currentLevel.max === Infinity ? Infinity : convertUsdToCurrency(profile.career.currentLevel.max, displayCurrency, exchangeRate),
        },
        nextLevel: profile.career.nextLevel ? {
          ...profile.career.nextLevel,
          min: convertUsdToCurrency(profile.career.nextLevel.min, displayCurrency, exchangeRate),
          max: profile.career.nextLevel.max === Infinity ? Infinity : convertUsdToCurrency(profile.career.nextLevel.max, displayCurrency, exchangeRate),
        } : undefined,
      },
    };
  }, [profile, contextCurrency, convertUsdToCurrency]);

  const handleCopyLink = useCallback(async () => {
    if (!profile?.referralLink) return;
    if (onHaptic) onHaptic('light');
    
    const success = await copyToClipboard(profile.referralLink);
    if (success) {
      hapticFeedback?.('notification', 'success');
      showTelegramAlert(t('profile.actions.copied'));
    }
  }, [profile?.referralLink, onHaptic, hapticFeedback, showTelegramAlert, copyToClipboard, t]);

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
    const currency = contextCurrency || profile?.currency || 'USD';
    const exchangeRate = profile?.exchangeRate || 1.0;
    const balance = convertedProfile?.balance || 0;
    
    const minAmountUSD = 10;
    const minAmount = currency === 'USD' ? minAmountUSD : minAmountUSD * exchangeRate;
    
    if (balance < minAmount) {
      const minDisplay = currency === 'USD' 
        ? '$10' 
        : `${Math.round(minAmount).toLocaleString()} ${currency}`;
      showModalAlert(
        t('profile.errors.insufficientFunds'), 
        t('profile.errors.minWithdrawal', { amount: minDisplay }), 
        'warning'
      );
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
        showModalAlert(t('profile.withdraw.submittedTitle'), t('profile.withdraw.submittedDesc'), 'success');
        await getProfile();
      },
    });
  }, [convertedProfile?.balance, contextCurrency, profile?.currency, profile?.exchangeRate, requestWithdrawal, getProfile, hapticFeedback, showWithdraw, showModalAlert, onHaptic, t]);

  const handleTopUp = useCallback(() => {
    const currency = contextCurrency || profile?.currency || 'USD';
    const exchangeRate = profile?.exchangeRate || 1.0;
    const balance = convertedProfile?.balance || 0;
    
    const minAmountUSD = 5;
    const minAmount = currency === 'USD' ? minAmountUSD : Math.round(minAmountUSD * exchangeRate);
    
    if (onHaptic) onHaptic('light');
    
    showTopUp({
      currency,
      balance,
      minAmount,
      onConfirm: async (amount: number) => {
        const result = await createTopUp(amount, currency);
        
        if (result.payment_url) {
          window.location.href = result.payment_url;
        }
      },
    });
  }, [contextCurrency, profile?.currency, profile?.exchangeRate, convertedProfile?.balance, createTopUp, showTopUp, onHaptic]);

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

  // Loading state
  if (!isInitialized || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            {t('profile.loading')}
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
          <div className="font-mono text-sm text-red-400 mb-2">{t('profile.error')}</div>
          <p className="text-gray-500 text-sm">{error || t('profile.loadFailed')}</p>
          <button
            onClick={() => getProfile()}
            className="mt-6 px-6 py-2 bg-white/10 border border-white/20 text-white text-xs font-mono uppercase hover:bg-white/20 transition-colors"
          >
            {t('profile.retry')}
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