/**
 * Leaderboard Adapter
 * 
 * Transforms API leaderboard data into component-friendly format.
 */

import type { APILeaderboardResponse, APILeaderboardEntry } from '../types/api';
import type { LeaderboardUser } from '../types/component';

/**
 * Generate trend indicator (random for now as backend doesn't track this)
 */
function generateTrend(): 'up' | 'down' | 'same' {
  const rand = Math.random();
  if (rand > 0.6) return 'up';
  if (rand > 0.3) return 'same';
  return 'down';
}

/**
 * Generate online status (random for non-current users)
 */
function generateStatus(): 'ONLINE' | 'AWAY' | 'BUSY' {
  const rand = Math.random();
  if (rand > 0.6) return 'ONLINE';
  if (rand > 0.3) return 'AWAY';
  return 'BUSY';
}

/**
 * Adapt single leaderboard entry
 */
function adaptLeaderboardEntry(entry: APILeaderboardEntry): LeaderboardUser {
  // Estimate market spend from savings (assuming ~20% average discount)
  const estimatedDiscount = 0.2;
  const marketSpend = entry.total_saved > 0 
    ? entry.total_saved / estimatedDiscount 
    : 0;
  const actualSpend = marketSpend - entry.total_saved;
  
  // Use photo_url from backend if available (saved from Telegram initData),
  // otherwise generate avatar via UI Avatars service based on name/telegram_id
  const avatarUrl = entry.photo_url 
    || `https://ui-avatars.com/api/?name=${encodeURIComponent(entry.name)}&background=0d1117&color=00ffff&size=160&font-size=0.4&bold=true`;
  
  return {
    rank: entry.rank,
    name: entry.name,
    handle: `@${entry.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`,
    marketSpend: Math.round(marketSpend),
    actualSpend: Math.round(actualSpend),
    saved: entry.total_saved,
    modules: entry.modules_count || 0, // Real count of delivered orders from API
    trend: generateTrend(),
    status: entry.is_current_user ? 'ONLINE' : generateStatus(),
    isMe: entry.is_current_user,
    avatarUrl,
  };
}

/**
 * Adapt API leaderboard response to component format
 */
export function adaptLeaderboard(
  response: APILeaderboardResponse,
  _currentUserId?: string, // Not needed anymore, backend sets is_current_user
  currency: string = 'USD' // Currency for formatting saved amounts
): LeaderboardUser[] {
  const { leaderboard, user_rank, user_saved } = response;
  
  // Adapt all leaderboard entries
  const adaptedUsers = leaderboard.map(entry => ({
    ...adaptLeaderboardEntry(entry),
    currency, // Add currency to each user entry
  }));
  
  // Check if current user is already in the list
  const currentUserInList = adaptedUsers.some(user => user.isMe);
  
  // If current user is NOT in the visible list but we have their rank/saved from API,
  // add them to the list so the sticky footer can show their position
  if (!currentUserInList && user_rank && user_rank > 0) {
    adaptedUsers.push({
      rank: user_rank,
      name: 'YOU',
      handle: '@you',
      marketSpend: user_saved > 0 ? Math.round(user_saved / 0.2) : 0,
      actualSpend: user_saved > 0 ? Math.round(user_saved / 0.2 - user_saved) : 0,
      saved: user_saved || 0,
      modules: 0,
      trend: 'same',
      status: 'ONLINE',
      isMe: true,
      currency,
      avatarUrl: `https://ui-avatars.com/api/?name=YOU&background=0d1117&color=00ffff&size=160&font-size=0.4&bold=true`,
    });
  }
  
  // Deduplicate by rank (in case backend sends duplicates)
  const seenRanks = new Set<number>();
  const uniqueUsers = adaptedUsers.filter(user => {
    if (seenRanks.has(user.rank)) {
      return false;
    }
    seenRanks.add(user.rank);
    return true;
  });
  
  // Sort by rank to ensure proper ordering
  return uniqueUsers.sort((a, b) => a.rank - b.rank);
}
