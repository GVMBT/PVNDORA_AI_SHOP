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
  const [isInitialized, setIsInitialized] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const { copy: copyToClipboard } = useClipboard();

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
    const currency = contextCurrency || profile?.currency || 'USD';
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
    }
    if (interface_language) {
      setLocale(interface_language as 'en' | 'ru' | 'uk' | 'de' | 'fr' | 'es' | 'tr' | 'ar' | 'hi');
    }
    
    try {
      // Update preferences via API (in background)
      const result = await updatePreferences(preferred_currency, interface_language);
      
      // NO PROFILE RELOAD NEEDED - Frontend converts balance locally using exchange_rate
      // Only reload if exchange_rate is missing (fallback for old API responses)
      if (preferred_currency && preferred_currency !== profile?.currency && !profile?.exchangeRate) {
        await getProfile(); // Fallback: reload to get exchange_rate
      }
      
      return result;
    } catch (error) {
      // Rollback on error: restore previous currency/language from profile
      if (profile) {
        if (preferred_currency) {
          setCurrency(profile.currency as 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED');
        }
        if (interface_language) {
          setLocale((profile.language || 'en') as 'en' | 'ru' | 'uk' | 'de' | 'fr' | 'es' | 'tr' | 'ar' | 'hi');
        }
      }
      throw error;
    }
  }, [updatePreferences, setCurrency, setLocale, getProfile, profile]);

  // Convert profile balance to current currency (for display)
  const convertedProfile = useMemo(() => {
    if (!profile) return null;
    
    const currentCurrency = contextCurrency || profile.currency;
    const exchangeRate = profile.exchangeRate || 1.0;
    
    // If currency matches profile currency, use existing converted values
    if (currentCurrency === profile.currency) {
      return profile;
    }
    
    // Convert USD amounts to current currency
    return {
      ...profile,
      balance: convertUsdToCurrency(profile.balanceUsd || profile.balance, currentCurrency, exchangeRate),
      earnedRef: convertUsdToCurrency(profile.earnedRefUsd || profile.earnedRef, currentCurrency, exchangeRate),
      saved: convertUsdToCurrency(profile.savedUsd || profile.saved, currentCurrency, exchangeRate),
      currency: currentCurrency,
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
