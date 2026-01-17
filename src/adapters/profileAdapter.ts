/**
 * Profile Adapter
 *
 * Transforms API profile data into component-friendly format.
 */

import type { APIProfileResponse, APIReferralNode, TelegramUser } from "../types/api";
import type { BillingLog, CareerLevel, NetworkNode, ProfileData } from "../types/component";

// After RUB-only migration, currency is always RUB (no conversion needed)

// Career levels are built dynamically from API thresholds (referral_settings table)
// No hardcoded values - thresholds come from referral_program.thresholds_usd

/**
 * Determine current career level based on turnover and VIP status
 *
 * @param turnoverUsd - Turnover in USD (for fallback comparison only)
 * @param thresholds - Thresholds for min/max (can be in display currency)
 * @param isVip - Whether user is VIP
 * @param effectiveLevel - Effective level from backend (0-3, calculated in USD)
 */
function getCurrentLevel(
  _turnoverUsd: number,
  thresholds: { level2: number; level3: number },
  isVip: boolean = false,
  effectiveLevel?: number
): CareerLevel {
  // Create level structure with provided thresholds (for min/max display)
  const levels: CareerLevel[] = [
    { id: 1, label: "PROXY", min: 0, max: thresholds.level2, color: "text-gray-400" },
    {
      id: 2,
      label: "OPERATOR",
      min: thresholds.level2,
      max: thresholds.level3,
      color: "text-purple-400",
    },
    { id: 3, label: "ARCHITECT", min: thresholds.level3, max: Infinity, color: "text-yellow-400" },
  ];

  // VIP users always get ARCHITECT level (level 3)
  if (isVip) {
    return levels[2]; // ARCHITECT
  }

  // Use effective_level from backend (always provided, calculated in USD on backend)
  // This is the source of truth for level determination
  if (effectiveLevel !== undefined && effectiveLevel >= 1 && effectiveLevel <= 3) {
    return levels[effectiveLevel - 1];
  }

  // Fallback: if effective_level not provided, use level 0 (LOCKED)
  // This should not happen in practice as backend always provides effective_level
  return levels[0];
}

/**
 * Get next career level
 */
function getNextLevel(
  currentLevel: CareerLevel,
  thresholds: { level2: number; level3: number }
): CareerLevel | undefined {
  const levels: CareerLevel[] = [
    { id: 1, label: "PROXY", min: 0, max: thresholds.level2, color: "text-gray-400" },
    {
      id: 2,
      label: "OPERATOR",
      min: thresholds.level2,
      max: thresholds.level3,
      color: "text-purple-400",
    },
    { id: 3, label: "ARCHITECT", min: thresholds.level3, max: Infinity, color: "text-yellow-400" },
  ];

  return levels.find((l) => l.id === currentLevel.id + 1);
}

/**
 * Calculate progress percentage within current level
 */
function _calculateProgressPercent(turnover: number, currentLevel: CareerLevel): number {
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
  type: "INCOME" | "OUTCOME"
): BillingLog {
  const date = new Date(item.created_at);
  const transactionType = type === "INCOME" ? "bonus" : "withdrawal";
  return {
    id: item.id.substring(0, 8).toUpperCase(),
    type,
    source: type === "INCOME" ? `REF_BONUS (L${item.level || 1})` : "WITHDRAWAL",
    amount: type === "INCOME" ? `+${item.amount.toFixed(2)}` : `-${item.amount.toFixed(2)}`,
    date: date
      .toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
      .replace(",", ""),
    transactionType, // For localization
  };
}

/**
 * Format balance transaction to billing log
 */
function formatBalanceTransactionLog(tx: {
  id: string;
  type: string;
  amount: number;
  description?: string;
  created_at: string;
  currency?: string;
  reference_type?: string;
  reference_id?: string;
  metadata?: Record<string, unknown>;
}): BillingLog {
  const date = new Date(tx.created_at);

  // Map transaction types to display types
  const typeMap: Record<string, "INCOME" | "OUTCOME" | "SYSTEM"> = {
    topup: "INCOME",
    purchase: "OUTCOME",
    refund: "INCOME",
    bonus: "INCOME",
    withdrawal: "OUTCOME",
    cashback: "INCOME",
    credit: "INCOME",
    debit: "OUTCOME",
    conversion: "SYSTEM",
  };

  const logType = typeMap[tx.type.toLowerCase()] || "SYSTEM";

  // Map transaction types to source labels
  const sourceMap: Record<string, string> = {
    topup: "TOP_UP",
    purchase: "PURCHASE",
    refund: "REFUND",
    bonus: "BONUS",
    withdrawal: "WITHDRAWAL",
    cashback: "CASHBACK",
    credit: "CREDIT",
    debit: "DEBIT",
    conversion: "CONVERSION",
  };

  const source = tx.description || sourceMap[tx.type.toLowerCase()] || tx.type.toUpperCase();

  // Format amount with sign
  const amountStr = logType === "OUTCOME" ? `-${tx.amount.toFixed(2)}` : `+${tx.amount.toFixed(2)}`;

  return {
    id: tx.id.substring(0, 8).toUpperCase(),
    type: logType,
    source,
    amount: amountStr,
    currency: tx.currency, // Pass through the currency from the transaction
    date: date
      .toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
      .replace(",", ""),
    transactionType: tx.type.toLowerCase(), // For localization
    // Extended info for detailed display
    referenceType: tx.reference_type,
    referenceId: tx.reference_id,
    metadata: tx.metadata as BillingLog["metadata"],
  };
}

/**
 * Adapt API profile response to component format
 */
export function adaptProfile(
  response: APIProfileResponse,
  telegramUser?: TelegramUser
): ProfileData {
  const {
    profile,
    referral_stats,
    referral_program,
    bonus_history,
    withdrawals,
    balance_transactions = [],
    // After RUB-only migration, currency fields are ignored
  } = response;

  // Use display thresholds (rounded for RUB: 20000/80000, USD: 250/1000) for UI
  // Level determination uses effective_level from backend (calculated in USD)
  const displayThresholds = referral_program.thresholds_display || referral_program.thresholds_usd;

  // Create level structure with display thresholds (for min/max display)
  // but use effective_level for actual level determination
  const currentLevel = getCurrentLevel(
    referral_program.turnover_usd, // Still in USD for comparison
    displayThresholds, // But use display thresholds for min/max
    referral_program.is_partner || false,
    referral_program.effective_level // Use backend-calculated level
  );

  const nextLevel = getNextLevel(currentLevel, displayThresholds);

  // Filter pending withdrawals (reserved balance)
  const pendingWithdrawals = withdrawals.filter((w) => w.status === "pending");

  // Combine and sort billing logs from multiple sources
  const billingLogs: BillingLog[] = [
    // Balance transactions (most comprehensive - includes topups, purchases, refunds, etc.)
    ...balance_transactions.map((tx) => formatBalanceTransactionLog(tx)),
    // Legacy referral bonuses (for backward compatibility)
    ...bonus_history.map((b) => formatBillingLog(b, "INCOME")),
    // Legacy withdrawals (for backward compatibility)
    ...withdrawals.map((w) => formatBillingLog({ ...w, level: undefined }, "OUTCOME")),
  ].sort((a, b) => {
    // Parse dates and sort descending (newest first)
    return (
      new Date(b.date.replace(" ", "T")).getTime() - new Date(a.date.replace(" ", "T")).getTime()
    );
  });

  // Calculate conversion rate
  const conversionRate =
    referral_stats.click_count > 0
      ? Number.parseFloat(
          ((referral_stats.level1_count / referral_stats.click_count) * 100).toFixed(1)
        )
      : 0;

  // Use telegramUser from initData first, fallback to profile data from DB
  const firstName = telegramUser?.first_name || profile.first_name || "Operative";
  const username = telegramUser?.username || profile.username;
  const telegramId = telegramUser?.id || profile.telegram_id;

  // Photo URL: prefer telegramUser (from initData), fallback to DB-stored, fallback to UI Avatars
  const photoUrl =
    telegramUser?.photo_url ||
    profile.photo_url ||
    `https://ui-avatars.com/api/?name=${encodeURIComponent(firstName)}&background=0d1117&color=00ffff&size=160&font-size=0.4&bold=true`;

  return {
    name: firstName,
    handle: username ? `@${username}` : `UID-${telegramId || Date.now()}`,
    // NOSONAR: Math.random() is safe for fallback display ID (not security-sensitive)
    id: telegramId
      ? `UID-${telegramId.toString().slice(-6)}`
      : `UID-${Math.random().toString(36).substring(2, 8).toUpperCase()}`, // NOSONAR
    // After RUB-only migration, all amounts are in RUB
    balance: profile.balance,
    balanceUsd: profile.balance_usd, // NOTE: Now contains RUB, name kept for compatibility
    balanceCurrency: "RUB", // Always RUB now
    earnedRef: profile.total_referral_earnings,
    earnedRefUsd: profile.total_referral_earnings_usd, // NOTE: Now contains RUB
    saved: profile.total_saved,
    savedUsd: profile.total_saved_usd, // NOTE: Now contains RUB
    role: (() => {
      if (profile.is_admin) return "ADMIN";
      if (referral_program.is_partner) return "VIP";
      return "USER";
    })(),
    isVip: referral_program.is_partner,
    partnerMode: referral_program.partner_mode || "commission",
    partnerDiscountPercent: referral_program.partner_discount_percent || 0,
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
      // Calculate progress: convert turnover to display currency and compare with anchor threshold
      // If next level already achieved (effective_level >= next_level), show 100%
      progressPercent: (() => {
        const effectiveLevel = referral_program.effective_level || 0;
        const nextLevelId = nextLevel?.id;

        // If next level already achieved, show 100%
        if (nextLevelId && effectiveLevel >= nextLevelId) {
          return 100;
        }

        // If no next level (max level), show 100%
        if (!nextLevel || currentLevel.max === Infinity) {
          return 100;
        }

        // All values are now in RUB - no conversion needed
        const turnoverDisplay = referral_program.turnover_usd; // Actually RUB after migration

        // Use anchor threshold in display currency for next level
        // next_threshold_display comes from backend (anchor threshold in display currency)
        let nextThresholdDisplay: number;
        if (
          referral_program.next_threshold_display !== undefined &&
          referral_program.next_threshold_display !== null
        ) {
          nextThresholdDisplay = referral_program.next_threshold_display;
        } else if (nextLevel) {
          // Fallback: use nextLevel.min (already in display currency from thresholds_display)
          nextThresholdDisplay = nextLevel.min;
        } else {
          return 0;
        }

        // Current level min in display currency (0 for level 1, threshold2 for level 2, etc.)
        // currentLevel.min is already in display currency (set from displayThresholds)
        const currentLevelMinDisplay = currentLevel.min; // 0 for PROXY, threshold2 for OPERATOR

        // Calculate progress: (turnover - level_start) / (level_end - level_start)
        // Both turnover and thresholds are now in the same currency (display currency)
        if (nextThresholdDisplay <= currentLevelMinDisplay) {
          return 0;
        }

        const progress = Math.min(
          100,
          Math.max(
            0,
            ((turnoverDisplay - currentLevelMinDisplay) /
              (nextThresholdDisplay - currentLevelMinDisplay)) *
              100
          )
        );
        return progress;
      })(),
      thresholds: referral_program.thresholds_display || referral_program.thresholds_usd, // Use anchor display thresholds if available, fallback to USD
      commissions: referral_program.commissions_percent || { level1: 10, level2: 7, level3: 3 }, // Commission percentages
    },
    networkTree: [], // Populated via adaptReferralNetwork call
    billingLogs,
    pendingWithdrawals: pendingWithdrawals.map((w) => ({
      id: w.id,
      amount_debited: w.amount_debited ?? w.amount,
      balance_currency: w.balance_currency || "RUB",
      amount_to_pay: w.amount_to_pay ?? 0,
      created_at: w.created_at,
    })),
    currency: "RUB", // Always RUB after migration
    language: profile.interface_language || "en",
    interfaceLanguage: profile.interface_language || undefined,
    photoUrl,
    exchangeRate: 1, // No conversion needed after RUB-only migration
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
    let rank = "PROXY";
    if (node.earnings_generated >= 1000) rank = "ARCHITECT";
    else if (node.earnings_generated >= 250) rank = "OPERATOR";

    // Determine status
    let status: "VIP" | "ACTIVE" | "SLEEP" = "ACTIVE";
    if (node.earnings_generated >= 500) status = "VIP";
    else if (node.order_count === 0) status = "SLEEP";

    // Photo URL with fallback to UI Avatars
    const nodeName = node.first_name || node.username || `User ${node.telegram_id}`;
    const photoUrl =
      node.photo_url ||
      `https://ui-avatars.com/api/?name=${encodeURIComponent(nodeName)}&background=0d1117&color=00ffff&size=80&font-size=0.4&bold=true`;

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
      // NOSONAR: Math.random() is safe for UI signal visualization
      signal: node.is_active ? 80 + Math.floor(Math.random() * 20) : Math.floor(Math.random() * 30), // NOSONAR
      lastActive: formatTimeAgo(node.created_at),
      invitedBy: null, // Set by parent context if needed
      activityData: generateMockActivity(node.order_count),
      photoUrl,
    };
  };

  return [
    ...level1.map((n) => mapNode(n, 1)),
    ...level2.map((n) => mapNode(n, 2)),
    ...level3.map((n) => mapNode(n, 3)),
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
 *
 * SECURITY: Math.random() is safe here - used only for UI visualization,
 * not for any security-sensitive operations.
 */
function generateMockActivity(orderCount: number): number[] {
  const base = Math.min(orderCount * 10, 50);
  // NOSONAR: Math.random() is safe for UI chart visualization
  return Array.from({ length: 7 }, () => Math.floor(base + Math.random() * (100 - base)));
}
