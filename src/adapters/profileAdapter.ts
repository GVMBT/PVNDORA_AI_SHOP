/**
 * Profile Adapter
 * 
 * Transforms API profile data into component-friendly format.
 */

import type { APIProfileResponse, APIReferralNode, TelegramUser } from '../types/api';
import type { ProfileData, CareerLevel, BillingLog, NetworkNode } from '../types/component';

// Career level definitions
const CAREER_LEVELS: CareerLevel[] = [
  { id: 1, label: 'PROXY', min: 0, max: 500, color: 'text-gray-400' },
  { id: 2, label: 'OPERATOR', min: 500, max: 2000, color: 'text-purple-400' },
  { id: 3, label: 'ARCHITECT', min: 2000, max: Infinity, color: 'text-yellow-400' },
];

/**
 * Determine current career level based on turnover
 */
function getCurrentLevel(turnoverUsd: number, thresholds: { level2: number; level3: number }): CareerLevel {
  const levels: CareerLevel[] = [
    { id: 1, label: 'PROXY', min: 0, max: thresholds.level2, color: 'text-gray-400' },
    { id: 2, label: 'OPERATOR', min: thresholds.level2, max: thresholds.level3, color: 'text-purple-400' },
    { id: 3, label: 'ARCHITECT', min: thresholds.level3, max: Infinity, color: 'text-yellow-400' },
  ];
  
  for (let i = levels.length - 1; i >= 0; i--) {
    if (turnoverUsd >= levels[i].min) {
      return levels[i];
    }
  }
  return levels[0];
}

/**
 * Get next career level
 */
function getNextLevel(currentLevel: CareerLevel, thresholds: { level2: number; level3: number }): CareerLevel | undefined {
  const levels: CareerLevel[] = [
    { id: 1, label: 'PROXY', min: 0, max: thresholds.level2, color: 'text-gray-400' },
    { id: 2, label: 'OPERATOR', min: thresholds.level2, max: thresholds.level3, color: 'text-purple-400' },
    { id: 3, label: 'ARCHITECT', min: thresholds.level3, max: Infinity, color: 'text-yellow-400' },
  ];
  
  return levels.find(l => l.id === currentLevel.id + 1);
}

/**
 * Calculate progress percentage within current level
 */
function calculateProgressPercent(turnover: number, currentLevel: CareerLevel): number {
  if (currentLevel.max === Infinity) return 100;
  const range = currentLevel.max - currentLevel.min;
  const progress = turnover - currentLevel.min;
  return Math.min(100, Math.max(0, (progress / range) * 100));
}

/**
 * Format billing log entry
 */
function formatBillingLog(
  item: { id: string; amount: number; level?: number; created_at: string },
  type: 'INCOME' | 'OUTCOME'
): BillingLog {
  const date = new Date(item.created_at);
  return {
    id: item.id.substring(0, 8).toUpperCase(),
    type,
    source: type === 'INCOME' ? `REF_BONUS (L${item.level || 1})` : 'WITHDRAWAL',
    amount: type === 'INCOME' ? `+${item.amount.toFixed(2)}` : `-${item.amount.toFixed(2)}`,
    date: date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).replace(',', ''),
  };
}

/**
 * Adapt API profile response to component format
 */
export function adaptProfile(
  response: APIProfileResponse,
  telegramUser?: TelegramUser
): ProfileData {
  const { profile, referral_stats, referral_program, bonus_history, withdrawals } = response;
  
  const currentLevel = getCurrentLevel(
    referral_program.turnover_usd,
    referral_program.thresholds_usd
  );
  
  const nextLevel = getNextLevel(currentLevel, referral_program.thresholds_usd);
  
  // Combine and sort billing logs
  const billingLogs: BillingLog[] = [
    ...bonus_history.map(b => formatBillingLog(b, 'INCOME')),
    ...withdrawals.map(w => formatBillingLog({ ...w, level: undefined }, 'OUTCOME')),
  ].sort((a, b) => {
    // Parse dates and sort descending
    return new Date(b.date.replace(' ', 'T')).getTime() - new Date(a.date.replace(' ', 'T')).getTime();
  });
  
  // Calculate conversion rate
  const conversionRate = referral_stats.click_count > 0
    ? parseFloat(((referral_stats.level1_count / referral_stats.click_count) * 100).toFixed(1))
    : 0;
  
  return {
    name: telegramUser?.first_name || 'Operative',
    handle: telegramUser?.username ? `@${telegramUser.username}` : `UID-${Date.now()}`,
    id: `UID-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
    balance: profile.balance,
    earnedRef: profile.total_referral_earnings,
    saved: profile.total_saved,
    role: profile.is_admin ? 'ADMIN' : (referral_program.is_partner ? 'VIP' : 'USER'),
    isVip: referral_program.is_partner,
    referralLink: profile.referral_link,
    stats: {
      referrals: referral_stats.level1_count,
      clicks: referral_stats.click_count,
      conversion: conversionRate,
      turnover: referral_program.turnover_usd,
    },
    career: {
      currentTurnover: referral_program.turnover_usd,
      currentLevel,
      nextLevel,
      progressPercent: calculateProgressPercent(referral_program.turnover_usd, currentLevel),
    },
    networkTree: [], // Populated via adaptReferralNetwork call
    billingLogs,
    currency: profile.currency,
  };
}

/**
 * Adapt referral network data from API to component format
 */
export function adaptReferralNetwork(
  level1: APIReferralNode[],
  level2: APIReferralNode[] = [],
  level3: APIReferralNode[] = []
): NetworkNode[] {
  const mapNode = (node: APIReferralNode, line: 1 | 2 | 3): NetworkNode => {
    // Determine rank based on earnings
    let rank = 'PROXY';
    if (node.earnings_generated >= 1000) rank = 'ARCHITECT';
    else if (node.earnings_generated >= 250) rank = 'OPERATOR';
    
    // Determine status
    let status: 'VIP' | 'ACTIVE' | 'SLEEP' = 'ACTIVE';
    if (node.earnings_generated >= 500) status = 'VIP';
    else if (node.order_count === 0) status = 'SLEEP';
    
    return {
      id: node.id,
      name: node.first_name || node.username || `User ${node.telegram_id}`,
      handle: node.username ? `@${node.username}` : `ID:${node.telegram_id}`,
      status,
      earned: node.earnings_generated,
      ordersCount: node.order_count,
      line,
      rank,
      volume: node.order_count * 50, // Approximate volume
      profit: node.earnings_generated,
      subs: 0, // Would need nested query
      signal: node.is_active ? 80 + Math.floor(Math.random() * 20) : Math.floor(Math.random() * 30),
      lastActive: formatTimeAgo(node.created_at),
      invitedBy: null, // Set by parent context if needed
      activityData: generateMockActivity(node.order_count),
    };
  };
  
  return [
    ...level1.map(n => mapNode(n, 1)),
    ...level2.map(n => mapNode(n, 2)),
    ...level3.map(n => mapNode(n, 3)),
  ];
}

/**
 * Format a timestamp to relative time
 */
function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

/**
 * Generate mock activity data for chart visualization
 */
function generateMockActivity(orderCount: number): number[] {
  const base = Math.min(orderCount * 10, 50);
  return Array.from({ length: 7 }, () => 
    Math.floor(base + Math.random() * (100 - base))
  );
}
