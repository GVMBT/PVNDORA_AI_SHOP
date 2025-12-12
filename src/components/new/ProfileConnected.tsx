/**
 * ProfileConnected
 * 
 * Connected version of Profile component with real API data.
 */

import React, { useEffect, useState, useCallback } from 'react';
import Profile from './Profile';
import { useProfileTyped } from '../../hooks/useApiTyped';
import { useTelegram } from '../../hooks/useTelegram';
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
  const { profile, getProfile, createShareLink, loading, error } = useProfileTyped();
  const { hapticFeedback, showPopup } = useTelegram();
  const [isInitialized, setIsInitialized] = useState(false);
  const [shareLoading, setShareLoading] = useState(false);

  useEffect(() => {
    const init = async () => {
      await getProfile();
      setIsInitialized(true);
    };
    init();
  }, [getProfile]);

  const handleCopyLink = useCallback(async () => {
    if (!profile?.referralLink) return;
    if (onHaptic) onHaptic('light');
    
    try {
      await navigator.clipboard.writeText(profile.referralLink);
      hapticFeedback?.('notification', 'success');
      showPopup?.({
        title: '✅',
        message: 'Ссылка скопирована!',
        buttons: [{ type: 'ok' }],
      });
    } catch (e) {
      console.error('Copy failed:', e);
    }
  }, [profile?.referralLink, onHaptic, hapticFeedback, showPopup]);

  const handleShare = useCallback(async () => {
    setShareLoading(true);
    if (onHaptic) onHaptic('medium');
    
    try {
      const { prepared_message_id } = await createShareLink();
      
      // Try Telegram's shareMessage first
      const tg = (window as any).Telegram?.WebApp;
      if (tg?.shareMessage) {
        tg.shareMessage(prepared_message_id, (success: boolean) => {
          if (success) console.log('Shared successfully');
        });
      } else if (tg?.switchInlineQuery) {
        tg.switchInlineQuery('invite', ['users', 'groups', 'channels']);
      } else {
        // Fallback to copy
        await handleCopyLink();
      }
    } catch (err) {
      console.error('Failed to share:', err);
      await handleCopyLink();
    } finally {
      setShareLoading(false);
    }
  }, [onHaptic, createShareLink, handleCopyLink]);

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
    />
  );
};

export default ProfileConnected;
