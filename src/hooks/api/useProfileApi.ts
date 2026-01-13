/**
 * Profile API Hook
 *
 * Type-safe hook for fetching profile and referral data.
 */

import { useState, useCallback } from "react";
import { useApi } from "../useApi";
import { logger } from "../../utils/logger";
import type { APIProfileResponse, APIReferralNetworkResponse } from "../../types/api";
import type { ProfileData } from "../../types/component";
import { adaptProfile, adaptReferralNetwork } from "../../adapters";
import { PAGINATION } from "../../config";

export function useProfileTyped() {
  const { get, post, put, loading, error } = useApi();
  const [profile, setProfile] = useState<ProfileData | null>(null);

  const getProfile = useCallback(async (): Promise<ProfileData | null> => {
    try {
      const response: APIProfileResponse = await get("/profile");
      const telegramUser = globalThis.Telegram?.WebApp?.initDataUnsafe?.user;
      const adapted = adaptProfile(response, telegramUser);

      // Also fetch referral network for all 3 levels
      try {
        const [level1Res, level2Res, level3Res] = (await Promise.all([
          get(`/referral/network?level=1&limit=${PAGINATION.REFERRAL_LIMIT}`),
          get(`/referral/network?level=2&limit=${PAGINATION.REFERRAL_LIMIT}`),
          get(`/referral/network?level=3&limit=${PAGINATION.REFERRAL_LIMIT}`),
        ])) as [APIReferralNetworkResponse, APIReferralNetworkResponse, APIReferralNetworkResponse];

        adapted.networkTree = adaptReferralNetwork(
          level1Res.referrals || [],
          level2Res.referrals || [],
          level3Res.referrals || []
        );
      } catch (networkErr) {
        logger.warn("Failed to fetch referral network, using empty tree", networkErr);
      }

      setProfile(adapted);
      return adapted;
    } catch (err) {
      logger.error("Failed to fetch profile", err);
      return null;
    }
  }, [get]);

  const previewWithdrawal = useCallback(
    async (
      amount: number
    ): Promise<{
      amount_requested: number;
      amount_requested_currency: string;
      amount_usd: number;
      amount_usdt_gross: number;
      network_fee: number;
      amount_usdt_net: number;
      exchange_rate: number;
      usdt_rate: number;
      can_withdraw: boolean;
      min_amount: number;
      max_amount: number;
      max_usdt_net: number;
    }> => {
      try {
        return await post("/profile/withdraw/preview", { amount });
      } catch (err) {
        logger.error("Failed to preview withdrawal", err);
        throw err;
      }
    },
    [post]
  );

  const requestWithdrawal = useCallback(
    async (
      amount: number,
      method: string,
      details: string
    ): Promise<{ success: boolean; message: string }> => {
      try {
        return await post("/profile/withdraw", { amount, method, details });
      } catch (err) {
        logger.error("Failed to request withdrawal", err);
        throw err;
      }
    },
    [post]
  );

  const createShareLink = useCallback(async (): Promise<{ prepared_message_id: string }> => {
    try {
      return await post("/referral/share-link", {});
    } catch (err) {
      logger.error("Failed to create share link", err);
      throw err;
    }
  }, [post]);

  const createTopUp = useCallback(
    async (
      amount: number,
      currency: string = "RUB"
    ): Promise<{ success: boolean; payment_url: string; topup_id: string; amount_rub: number }> => {
      try {
        return await post("/profile/topup", { amount, currency });
      } catch (err) {
        logger.error("Failed to create top-up", err);
        throw err;
      }
    },
    [post]
  );

  const updatePreferences = useCallback(
    async (
      preferred_currency?: string,
      interface_language?: string
    ): Promise<{ success: boolean; message: string }> => {
      try {
        return await put("/profile/preferences", { preferred_currency, interface_language });
      } catch (err) {
        logger.error("Failed to update preferences", err);
        throw err;
      }
    },
    [put]
  );

  const setPartnerMode = useCallback(
    async (
      mode: "commission" | "discount",
      discountPercent: number = 15
    ): Promise<{ success: boolean; mode: string; discount_percent: number; message: string }> => {
      try {
        return await post("/partner/mode", { mode, discount_percent: discountPercent });
      } catch (err) {
        logger.error("Failed to set partner mode", err);
        throw err;
      }
    },
    [post]
  );

  const submitPartnerApplication = useCallback(
    async (
      email: string,
      phone: string,
      source: string,
      audienceSize: string,
      description: string,
      expectedVolume?: string,
      socialLinks?: Record<string, string>
    ): Promise<{ success: boolean; message: string; application_id?: string }> => {
      try {
        return await post("/partner/apply", {
          email,
          phone,
          source,
          audience_size: audienceSize,
          description,
          expected_volume: expectedVolume,
          social_links: socialLinks,
        });
      } catch (err) {
        logger.error("Failed to submit partner application", err);
        throw err;
      }
    },
    [post]
  );

  const getPartnerApplicationStatus = useCallback(async (): Promise<{
    is_partner: boolean;
    application: { id: string; status: string; created_at: string; admin_comment?: string } | null;
    can_apply: boolean;
  }> => {
    try {
      return await get("/partner/application-status");
    } catch (err) {
      logger.error("Failed to get partner application status", err);
      throw err;
    }
  }, [get]);

  return {
    profile,
    getProfile,
    previewWithdrawal,
    requestWithdrawal,
    createShareLink,
    createTopUp,
    updatePreferences,
    setPartnerMode,
    submitPartnerApplication,
    getPartnerApplicationStatus,
    loading,
    error,
  };
}
