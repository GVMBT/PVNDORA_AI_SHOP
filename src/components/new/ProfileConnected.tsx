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
  const { profile, getProfile, previewWithdrawal, requestWithdrawal, createShareLink, createTopUp, updatePreferences, setPartnerMode, submitPartnerApplication, getPartnerApplicationStatus, loading, error } = useProfileTyped();
  const { hapticFeedback, showConfirm, openLink, showAlert: showTelegramAlert } = useTelegram();
  const { showTopUp, showWithdraw, showAlert: showModalAlert } = useCyberModal();
  const { updateFromProfile, setCurrency, setLocale, setExchangeRate, currency: contextCurrency } = useLocaleContext();
  const { t, formatPrice } = useLocale();
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

  // Convert USD values to display currency
  // Uses balanceUsd (always USD from backend) and converts to contextCurrency
  // This handles the case when user changes currency in UI settings
  const convertedProfile = useMemo(() => {
    if (!profile) return null;
    
    // Use context currency if set, otherwise profile currency, default to USD
    const displayCurrency = contextCurrency || profile.currency || 'USD';
    const exchangeRate = profile.exchangeRate || 1.0;
    
    // CRITICAL: Save original balance in balance_currency BEFORE conversion
    // profile.balance from backend is already in balance_currency (RUB for ru users, USD for others)
    const originalBalanceInBalanceCurrency = profile.balance || 0;
    
    // Always use _usd values (base amounts from DB) for conversion
    const balanceUsd = profile.balanceUsd ?? 0;
    const earnedRefUsd = profile.earnedRefUsd ?? 0;
    const savedUsd = profile.savedUsd ?? 0;
    
    // Helper for conversion
    const convert = (usd: number): number => {
      if (displayCurrency === 'USD' || exchangeRate === 1.0) return usd;
      const converted = usd * exchangeRate;
      // Round integer currencies
      return ['RUB', 'UAH', 'TRY', 'INR'].includes(displayCurrency) 
        ? Math.round(converted) 
        : Math.round(converted * 100) / 100;
    };
    
    return {
      ...profile,
      currency: displayCurrency,
      // For display: use converted balance
      balance: convert(balanceUsd),
      // CRITICAL: Keep original balance in balance_currency for withdrawals
      // This is the actual balance stored in DB in user's balance_currency
      balanceInBalanceCurrency: originalBalanceInBalanceCurrency,
      earnedRef: convert(earnedRefUsd),
      saved: convert(savedUsd),
      career: {
        ...profile.career,
        // Convert turnover from USD to display currency for progress calculation
        currentTurnover: convert(profile.career.currentTurnover),
        // Min/max are in display currency if thresholds_display was used (anchor thresholds)
        // If thresholds_display not available, they're in USD and need conversion
        // Backend always returns thresholds_display, so min/max should already be in correct currency
        currentLevel: {
          ...profile.career.currentLevel,
          // Backend always provides thresholds_display, so min/max are already in display currency
          // min: 0 for PROXY, threshold2_display for OPERATOR, threshold3_display for ARCHITECT
          // max: threshold2_display for PROXY, threshold3_display for OPERATOR, Infinity for ARCHITECT
          min: profile.career.currentLevel.min,
          max: profile.career.currentLevel.max,
        },
        nextLevel: profile.career.nextLevel ? {
          ...profile.career.nextLevel,
          min: profile.career.nextLevel.min,
          max: profile.career.nextLevel.max,
        } : undefined,
      },
    };
  }, [profile, contextCurrency]);

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

  const handleWithdraw = useCallback(async () => {
    const currency = contextCurrency || profile?.currency || 'USD';
    // CRITICAL: Use original balance in balance_currency, NOT converted balance
    // balance_currency is the actual currency of user's balance in DB (RUB for ru users, USD for others)
    const balanceCurrency = profile?.balanceCurrency || profile?.currency || 'USD';
    // Get original balance in balance_currency (before conversion to display currency)
    // convertedProfile.balanceInBalanceCurrency contains the actual balance from DB
    const originalBalance = convertedProfile?.balanceInBalanceCurrency ?? profile?.balance ?? 0;
    
    if (originalBalance <= 0) {
      showModalAlert(
        t('profile.errors.insufficientFunds'), 
        t('profile.errors.insufficientBalance'), 
        'warning'
      );
      return;
    }
    
    try {
      // Get preview with original balance in balance_currency (NOT converted to display currency)
      const preview = await previewWithdrawal(originalBalance);
      
      if (!preview.can_withdraw || preview.max_amount <= 0) {
        // Format min_amount with currency from response (min_amount is in balance_currency)
        const minAmountFormatted = formatPrice(
          preview.min_amount, 
          preview.amount_requested_currency || currency
        );
        showModalAlert(
          t('profile.errors.insufficientFunds'), 
          t('profile.errors.minWithdrawal', { amount: minAmountFormatted }), 
          'warning'
        );
        return;
      }
      
      if (onHaptic) onHaptic('medium');
      
      // Use converted balance for UI display (in display currency)
      const displayBalance = convertedProfile?.balance || 0;
      
      showWithdraw({
        currency: preview.amount_requested_currency || currency,  // Use balance_currency from backend
        balance: originalBalance,  // Use original balance in balance_currency for validation
        minAmount: preview.min_amount,  // Already in balance_currency
        maxAmount: preview.max_amount,  // Already in balance_currency
        previewWithdrawal,
        onConfirm: async (amount: number, method: string, details: string) => {
          await requestWithdrawal(amount, method, details);
          hapticFeedback?.('notification', 'success');
          showModalAlert(t('profile.withdraw.submittedTitle'), t('profile.withdraw.submittedDesc'), 'success');
          await getProfile();
        },
      });
    } catch (err) {
      logger.error('Failed to preview withdrawal', err);
      showModalAlert(
        t('profile.errors.error'), 
        'Не удалось загрузить информацию о выводе. Попробуйте позже.',
        'warning'
      );
    }
  }, [convertedProfile?.balance, contextCurrency, profile?.currency, previewWithdrawal, requestWithdrawal, getProfile, hapticFeedback, showWithdraw, showModalAlert, onHaptic, t]);

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