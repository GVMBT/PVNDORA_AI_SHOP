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
  
  // Try to construct Telegram avatar URL if we have telegram_id
  // Uses Telegram's CDN - may not work for all users (privacy settings)
  const avatarUrl = entry.telegram_id 
    ? `https://t.me/i/userpic/160/${entry.telegram_id}.jpg`
    : undefined;
  
  return {
    rank: entry.rank,
    name: entry.name,
    handle: `@${entry.name.toLowerCase().replace(/[^a-z0-9]/g, '')}`,
    marketSpend: Math.round(marketSpend),
    actualSpend: Math.round(actualSpend),
    saved: entry.total_saved,
    modules: Math.floor(Math.random() * 15) + 1, // Not tracked in API
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
  _currentUserId?: string // Not needed anymore, backend sets is_current_user
): LeaderboardUser[] {
  const { leaderboard, user_rank, user_saved } = response;
  
  // Adapt all leaderboard entries
  const adaptedUsers = leaderboard.map(adaptLeaderboardEntry);
  
  // Check if current user is already in the list
  const currentUserInList = adaptedUsers.some(u => u.isMe);
  
  // If current user has a rank but isn't in top list, add them
  if (user_rank && user_saved !== undefined && !currentUserInList) {
    const marketSpend = user_saved > 0 ? user_saved / 0.2 : 0;
    adaptedUsers.push({
      rank: user_rank,
      name: 'YOU',
      handle: '@you',
      marketSpend: Math.round(marketSpend),
      actualSpend: Math.round(marketSpend - user_saved),
      saved: user_saved,
      modules: 1,
      trend: 'same',
      status: 'ONLINE',
      isMe: true,
    });
  }
  
  // Sort by rank
  return adaptedUsers.sort((a, b) => a.rank - b.rank);
}
