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
import { PartnerApplicationModal, type PartnerApplicationData } from '../profile';
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
  const { profile, getProfile, requestWithdrawal, createShareLink, createTopUp, updatePreferences, setPartnerMode, submitPartnerApplication, getPartnerApplicationStatus, loading, error } = useProfileTyped();
  const { hapticFeedback, showConfirm, openLink, showAlert: showTelegramAlert } = useTelegram();
  const { showTopUp, showWithdraw, showAlert: showModalAlert } = useCyberModal();
  const { updateFromProfile, setCurrency, setLocale, setExchangeRate, currency: contextCurrency } = useLocaleContext();
  const { t } = useLocale();
  const { clearCartState } = useCart();
  const [isInitialized, setIsInitialized] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const { copy: copyToClipboard } = useClipboard();
  
  // Partner application state
  const [showPartnerModal, setShowPartnerModal] = useState(false);
  const [partnerApplication, setPartnerApplication] = useState<{
    status: string;
    created_at: string;
    admin_comment?: string;
  } | null>(null);

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
    
    // CRITICAL: Always use _usd values for conversion (they are base USD amounts)
    // profile.balance is already converted to user currency, so we MUST use balanceUsd
    const balanceUsd = profile.balanceUsd ?? 0;
    const earnedRefUsd = profile.earnedRefUsd ?? 0;
    const savedUsd = profile.savedUsd ?? 0;
    
    // If currency is USD, use USD values directly
    if (displayCurrency === 'USD') {
      return {
        ...profile,
        currency: displayCurrency,
        balance: balanceUsd,
        earnedRef: earnedRefUsd,
        saved: savedUsd,
      };
    }
    
    // Convert all USD amounts to display currency
    const convertedBalance = convertUsdToCurrency(balanceUsd, displayCurrency, exchangeRate);
    const convertedEarnedRef = convertUsdToCurrency(earnedRefUsd, displayCurrency, exchangeRate);
    const convertedSaved = convertUsdToCurrency(savedUsd, displayCurrency, exchangeRate);
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
    // Use USD balance for comparison since minimum is defined in USD
    const balanceUSD = profile?.balanceUsd || 0;
    
    // Minimum withdrawal: $5 USD (matches backend MIN_WITHDRAWAL_USD)
    const minAmountUSD = 5;
    
    if (balanceUSD < minAmountUSD) {
      // Show minimum in user's preferred currency for clarity
      const minDisplay = currency === 'USD' 
        ? `$${minAmountUSD}` 
        : `${Math.round(minAmountUSD * exchangeRate).toLocaleString()} ${currency}`;
      showModalAlert(
        t('profile.errors.insufficientFunds'), 
        t('profile.errors.minWithdrawal', { amount: minDisplay }), 
        'warning'
      );
      return;
    }
    
    // Balance to display in withdrawal modal (in user's currency)
    const balance = convertedProfile?.balance || 0;
    const minAmount = currency === 'USD' ? minAmountUSD : Math.round(minAmountUSD * exchangeRate);
    
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
  }, [convertedProfile?.balance, contextCurrency, profile?.balanceUsd, profile?.currency, profile?.exchangeRate, requestWithdrawal, getProfile, hapticFeedback, showWithdraw, showModalAlert, onHaptic, t]);

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
    logger.info('handleUpdatePreferences called', { preferred_currency, interface_language });
    
    // Optimistic update: change context IMMEDIATELY (UI updates right away)
    if (preferred_currency) {
      logger.info('Setting currency optimistically to', preferred_currency);
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
      logger.info('Calling updatePreferences API');
      const result = await updatePreferences(preferred_currency, interface_language);
      logger.info('updatePreferences API result', result);
      
      // Always reload profile when currency changes to get correct exchange_rate for new currency
      if (preferred_currency) {
        logger.info('Reloading profile to get exchange_rate for new currency');
        const updatedProfile = await getProfile(); // Reload to get exchange_rate for new currency
        // Синхронизируем контекст с обновленным профилем
        if (updatedProfile) {
          logger.info('Updating context from profile with new currency', preferred_currency);
          // Update context from profile (this will sync exchange rate and other data)
          updateFromProfile(updatedProfile);
          // Explicitly set currency again to ensure it matches user's selection
          setCurrency(preferred_currency as 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED');
        }
      }
      
      return result;
    } catch (error) {
      logger.error('Error updating preferences', error);
      // Rollback on error: restore previous currency/language from profile
      if (profile) {
        if (preferred_currency) {
          logger.info('Rolling back currency to', profile.currency);
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
  }, [updatePreferences, setCurrency, setLocale, setExchangeRate, getProfile, profile, clearCartState]);

  // Handler for toggling partner reward mode
  // MUST be before conditional returns (React hooks rule)
  const handleSetPartnerMode = useCallback(async (mode: 'commission' | 'discount') => {
    try {
      const result = await setPartnerMode(mode);
      if (result.success) {
        hapticFeedback?.('notification', 'success');
        // Refresh profile to get updated mode
        await getProfile();
      }
      return result;
    } catch (err) {
      hapticFeedback?.('notification', 'error');
      throw err;
    }
  }, [setPartnerMode, hapticFeedback, getProfile]);

  // Handler for opening partner application modal
  const handleOpenPartnerApplication = useCallback(async () => {
    if (onHaptic) onHaptic('light');
    
    // Check existing application status
    try {
      const status = await getPartnerApplicationStatus();
      if (status.application) {
        setPartnerApplication({
          status: status.application.status,
          created_at: status.application.created_at,
          admin_comment: status.application.admin_comment,
        });
      } else {
        setPartnerApplication(null);
      }
    } catch (err) {
      // Ignore error, will show form anyway
      setPartnerApplication(null);
    }
    
    setShowPartnerModal(true);
  }, [getPartnerApplicationStatus, onHaptic]);

  // Handler for submitting partner application
  const handleSubmitPartnerApplication = useCallback(async (data: PartnerApplicationData) => {
    try {
      const result = await submitPartnerApplication(
        data.email,
        data.phone,
        data.source,
        data.audienceSize,
        data.description,
        data.expectedVolume,
        data.socialLinks
      );
      
      if (result.success) {
        hapticFeedback?.('notification', 'success');
      }
      
      return result;
    } catch (err) {
      hapticFeedback?.('notification', 'error');
      return { success: false, message: err instanceof Error ? err.message : 'Ошибка отправки' };
    }
  }, [submitPartnerApplication, hapticFeedback]);

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
    <>
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
        onSetPartnerMode={handleSetPartnerMode}
        onApplyPartner={handleOpenPartnerApplication}
      />
      
      {/* Partner Application Modal */}
      <PartnerApplicationModal
        isOpen={showPartnerModal}
        onClose={() => setShowPartnerModal(false)}
        onSubmit={handleSubmitPartnerApplication}
        existingApplication={partnerApplication}
      />
    </>
  );
};

export default ProfileConnected;