/**
 * Profile Adapter
 * 
 * Transforms API profile data into component-friendly format.
 */

import type { APIProfileResponse, APIReferralNode, TelegramUser } from '../types/api';
import type { ProfileData, CareerLevel, BillingLog, NetworkNode } from '../types/component';

// Career levels are built dynamically from API thresholds (referral_settings table)
// No hardcoded values - thresholds come from referral_program.thresholds_usd

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
 * Format billing log entry (for referral bonuses and withdrawals)
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
 * Format balance transaction to billing log
 */
function formatBalanceTransactionLog(
  tx: { id: string; type: string; amount: number; description?: string; created_at: string; currency?: string }
): BillingLog {
  const date = new Date(tx.created_at);
  
  // Map transaction types to display types
  const typeMap: Record<string, 'INCOME' | 'OUTCOME' | 'SYSTEM'> = {
    'topup': 'INCOME',
    'purchase': 'OUTCOME',
    'refund': 'INCOME',
    'bonus': 'INCOME',
    'withdrawal': 'OUTCOME',
    'cashback': 'INCOME',
    'credit': 'INCOME',
    'debit': 'OUTCOME',
  };
  
  const logType = typeMap[tx.type.toLowerCase()] || 'SYSTEM';
  
  // Map transaction types to source labels
  const sourceMap: Record<string, string> = {
    'topup': 'TOP_UP',
    'purchase': 'PURCHASE',
    'refund': 'REFUND',
    'bonus': 'BONUS',
    'withdrawal': 'WITHDRAWAL',
    'cashback': 'CASHBACK',
    'credit': 'CREDIT',
    'debit': 'DEBIT',
  };
  
  const source = tx.description || sourceMap[tx.type.toLowerCase()] || tx.type.toUpperCase();
  
  // Format amount with sign
  const amountStr = logType === 'OUTCOME' 
    ? `-${tx.amount.toFixed(2)}`
    : `+${tx.amount.toFixed(2)}`;
  
  return {
    id: tx.id.substring(0, 8).toUpperCase(),
    type: logType,
    source,
    amount: amountStr,
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
  const { profile, referral_stats, referral_program, bonus_history, withdrawals, balance_transactions = [] } = response;
  
  const currentLevel = getCurrentLevel(
    referral_program.turnover_usd,
    referral_program.thresholds_usd
  );
  
  const nextLevel = getNextLevel(currentLevel, referral_program.thresholds_usd);
  
  // Combine and sort billing logs from multiple sources
  const billingLogs: BillingLog[] = [
    // Balance transactions (most comprehensive - includes topups, purchases, refunds, etc.)
    ...balance_transactions.map(tx => formatBalanceTransactionLog(tx)),
    // Legacy referral bonuses (for backward compatibility)
    ...bonus_history.map(b => formatBillingLog(b, 'INCOME')),
    // Legacy withdrawals (for backward compatibility)
    ...withdrawals.map(w => formatBillingLog({ ...w, level: undefined }, 'OUTCOME')),
  ].sort((a, b) => {
    // Parse dates and sort descending (newest first)
    return new Date(b.date.replace(' ', 'T')).getTime() - new Date(a.date.replace(' ', 'T')).getTime();
  });
  
  // Calculate conversion rate
  const conversionRate = referral_stats.click_count > 0
    ? parseFloat(((referral_stats.level1_count / referral_stats.click_count) * 100).toFixed(1))
    : 0;
  
  // Use telegramUser from initData first, fallback to profile data from DB
  const firstName = telegramUser?.first_name || profile.first_name || 'Operative';
  const username = telegramUser?.username || profile.username;
  const telegramId = telegramUser?.id || profile.telegram_id;
  
  // Photo URL: prefer telegramUser (from initData), fallback to DB-stored, fallback to UI Avatars
  const photoUrl = telegramUser?.photo_url 
    || profile.photo_url 
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(firstName)}&background=0d1117&color=00ffff&size=160&font-size=0.4&bold=true`;
  
  return {
    name: firstName,
    handle: username ? `@${username}` : `UID-${telegramId || Date.now()}`,
    id: telegramId ? `UID-${telegramId.toString().slice(-6)}` : `UID-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
    balance: profile.balance,  // Converted for backward compatibility
    balanceUsd: profile.balance_usd || profile.balance,  // USD amount for frontend conversion
    earnedRef: profile.total_referral_earnings,  // Converted
    earnedRefUsd: profile.total_referral_earnings_usd || profile.total_referral_earnings,  // USD amount
    saved: profile.total_saved,  // Converted
    savedUsd: profile.total_saved_usd || profile.total_saved,  // USD amount
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
    language: profile.interface_language || 'en',
    interfaceLanguage: profile.interface_language || undefined,
    photoUrl,
    exchangeRate: response.exchange_rate || 1.0,  // Exchange rate for frontend conversion
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
    
    // Photo URL with fallback to UI Avatars
    const nodeName = node.first_name || node.username || `User ${node.telegram_id}`;
    const photoUrl = node.photo_url 
      || `https://ui-avatars.com/api/?name=${encodeURIComponent(nodeName)}&background=0d1117&color=00ffff&size=80&font-size=0.4&bold=true`;
    
    return {
      id: node.id,
      name: nodeName,
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
      photoUrl,
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
