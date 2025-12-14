/**
 * API Hooks Barrel Export
 * 
 * Re-exports all domain-specific API hooks for easy importing.
 */

// Products
export { useProductsTyped } from './useProductsApi';

// Orders
export { useOrdersTyped } from './useOrdersApi';

// Profile
export { useProfileTyped } from './useProfileApi';

// Leaderboard
export { useLeaderboardTyped } from './useLeaderboardApi';

// Support (Reviews, Tickets, AI Chat)
export { useReviewsTyped, useSupportTyped, useAIChatTyped } from './useSupportApi';

// Admin
export {
  useAdminProductsTyped,
  useAdminOrdersTyped,
  useAdminUsersTyped,
  useAdminAnalyticsTyped,
  type AdminProduct,
  type AdminOrder,
  type AdminUser,
  type AdminAnalytics,
} from './useAdminApi';
