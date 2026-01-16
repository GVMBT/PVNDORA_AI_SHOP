/**
 * Profile Component Types
 *
 * Shared type definitions for profile components.
 */

import type { CurrencyCode } from "../../utils/currency";

export interface CareerLevelData {
  id: number;
  label: string;
  min: number;
  max: number;
  color: string;
}

export interface NetworkNodeData {
  id: string | number;
  name?: string;
  handle: string;
  status: "active" | "inactive";
  earned: number;
  ordersCount: number;
  photoUrl?: string;
  rank?: string;
  profit?: number;
  volume?: number;
  signal?: number;
  subs?: number;
  lastActive?: string;
  invitedBy?: string;
  line?: number;
  activityData?: number[];
}

export interface BillingLogData {
  id: string;
  type: "INCOME" | "OUTCOME" | "SYSTEM";
  source: string;
  amount: string;
  date: string;
  transactionType?: string; // For localization: topup, purchase, refund, etc.
  currency?: string; // Currency of the transaction (e.g., 'RUB', 'USD') - if same as user's currency, no conversion needed
  // Extended info
  referenceType?: string; // 'order', 'withdrawal', 'referral', 'admin_adjustment', etc.
  referenceId?: string; // ID of the related entity
  metadata?: {
    order_id?: string;
    product_name?: string;
    payment_method?: string;
    from_username?: string; // For referral bonuses
    level?: number; // For referral bonuses (1, 2, 3)
    percent?: number; // Bonus/cashback percent
    refund_reason?: string;
    [key: string]: unknown;
  };
}

export interface ProfileStatsData {
  referrals: number;
  clicks: number;
  conversion: number;
  turnover: number;
}

export interface CareerProgressData {
  currentTurnover: number;
  currentLevel: CareerLevelData;
  nextLevel?: CareerLevelData;
  thresholds?: { level2: number; level3: number }; // USD thresholds
  commissions?: { level1: number; level2: number; level3: number }; // Commission percentages
  progressPercent: number;
}

export interface ProfileDataProp {
  name: string;
  handle: string;
  id: string;
  balance: number;
  earnedRef: number;
  saved: number;
  role: "USER" | "VIP" | "ADMIN";
  isVip: boolean;
  referralLink: string;
  stats: ProfileStatsData;
  career: CareerProgressData;
  networkTree: NetworkNodeData[];
  billingLogs: BillingLogData[];
  currency: CurrencyCode;
  language?: string; // User's interface language (ru, en)
  photoUrl?: string;
  partnerMode?: "commission" | "discount"; // Partner reward mode
  exchangeRate?: number; // Currency exchange rate from USD
}
