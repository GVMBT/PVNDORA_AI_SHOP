/**
 * Profile Component Types
 * 
 * Shared type definitions for profile components.
 */

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
  status: 'active' | 'inactive' | string;
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
  type: 'INCOME' | 'OUTCOME' | 'SYSTEM';
  source: string;
  amount: string;
  date: string;
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
  progressPercent: number;
}

export interface ProfileDataProp {
  name: string;
  handle: string;
  id: string;
  balance: number;
  earnedRef: number;
  saved: number;
  role: 'USER' | 'VIP' | 'ADMIN';
  isVip: boolean;
  referralLink: string;
  stats: ProfileStatsData;
  career: CareerProgressData;
  networkTree: NetworkNodeData[];
  billingLogs: BillingLogData[];
  currency: string;
  photoUrl?: string;
}







