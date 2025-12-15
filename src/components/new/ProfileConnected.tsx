/**
 * ProfileConnected
 * 
 * Connected version of Profile component with real API data.
 */

import React, { useEffect, useState, useCallback } from 'react';
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
  const { updateFromProfile, setCurrency, setLocale } = useLocaleContext();
  const [isInitialized, setIsInitialized] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);
  const { copy: copyToClipboard } = useClipboard();

  useEffect(() => {
    const init = async () => {
      await getProfile();
      setIsInitialized(true);
    };
    init();
  }, [getProfile]);

  // Update locale context when profile changes
  useEffect(() => {
    if (profile) {
      updateFromProfile(profile);
    }
  }, [profile, updateFromProfile]);

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
    const minAmount = 500;
    
    if (balance < minAmount) {
        showModalAlert('INSUFFICIENT FUNDS', `Minimum withdrawal is ${minAmount} ${currency}`, 'warning');
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
    const currency = profile?.currency || 'RUB';
    const balance = profile?.balance || 0;
    const minAmount = currency === 'USD' ? 5 : 500;
    
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
  }, [profile?.currency, profile?.balance, createTopUp, showTopUp, onHaptic]);

  // CRITICAL: All hooks must be called BEFORE any conditional returns
  const handleUpdatePreferences = useCallback(async (preferred_currency?: string, interface_language?: string) => {
    // Update preferences via API
    const result = await updatePreferences(preferred_currency, interface_language);
    
    // Update locale context immediately (no reload needed)
    if (preferred_currency) {
      setCurrency(preferred_currency as 'USD' | 'RUB' | 'EUR' | 'UAH' | 'TRY' | 'INR' | 'AED');
    }
    if (interface_language) {
      setLocale(interface_language as 'en' | 'ru' | 'uk' | 'de' | 'fr' | 'es' | 'tr' | 'ar' | 'hi');
    }
    
    // Reload profile to get updated data (prices will be recalculated with new currency)
    await getProfile();
    
    return result;
  }, [updatePreferences, setCurrency, setLocale, getProfile]);

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
        profile={profile}
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
