/**
 * Profile API Hook
 * 
 * Type-safe hook for fetching profile and referral data.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';
import type { APIProfileResponse, APIReferralNetworkResponse } from '../../types/api';
import type { ProfileData } from '../../types/component';
import { adaptProfile, adaptReferralNetwork } from '../../adapters';

export function useProfileTyped() {
  const { get, post, loading, error } = useApi();
  const [profile, setProfile] = useState<ProfileData | null>(null);

  const getProfile = useCallback(async (): Promise<ProfileData | null> => {
    try {
      const response: APIProfileResponse = await get('/profile');
      const telegramUser = (window as any).Telegram?.WebApp?.initDataUnsafe?.user;
      const adapted = adaptProfile(response, telegramUser);
      
      // Also fetch referral network for all 3 levels
      try {
        const [level1Res, level2Res, level3Res] = await Promise.all([
          get('/referral/network?level=1&limit=50'),
          get('/referral/network?level=2&limit=50'),
          get('/referral/network?level=3&limit=50'),
        ]) as [APIReferralNetworkResponse, APIReferralNetworkResponse, APIReferralNetworkResponse];
        
        adapted.networkTree = adaptReferralNetwork(
          level1Res.referrals || [],
          level2Res.referrals || [],
          level3Res.referrals || []
        );
      } catch (networkErr) {
        console.warn('Failed to fetch referral network, using empty tree:', networkErr);
      }
      
      setProfile(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch profile:', err);
      return null;
    }
  }, [get]);

  const requestWithdrawal = useCallback(async (
    amount: number,
    method: string,
    details: string
  ): Promise<{ success: boolean; message: string }> => {
    try {
      return await post('/profile/withdraw', { amount, method, details });
    } catch (err) {
      console.error('Failed to request withdrawal:', err);
      throw err;
    }
  }, [post]);

  const createShareLink = useCallback(async (): Promise<{ prepared_message_id: string }> => {
    try {
      return await post('/referral/share-link', {});
    } catch (err) {
      console.error('Failed to create share link:', err);
      throw err;
    }
  }, [post]);

  const createTopUp = useCallback(async (
    amount: number,
    currency: string = 'RUB'
  ): Promise<{ success: boolean; payment_url: string; topup_id: string; amount_rub: number }> => {
    try {
      return await post('/profile/topup', { amount, currency });
    } catch (err) {
      console.error('Failed to create top-up:', err);
      throw err;
    }
  }, [post]);

  const updatePreferences = useCallback(async (
    preferred_currency?: string,
    interface_language?: string
  ): Promise<{ success: boolean; message: string }> => {
    try {
      return await post('/profile/preferences', { preferred_currency, interface_language });
    } catch (err) {
      console.error('Failed to update preferences:', err);
      throw err;
    }
  }, [post]);

  return { profile, getProfile, requestWithdrawal, createShareLink, createTopUp, updatePreferences, loading, error };
}
