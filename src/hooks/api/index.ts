/**
 * API Hooks Barrel Export
 *
 * Re-exports all domain-specific API hooks for easy importing.
 */

// Admin
export {
  type AdminAnalytics,
  type AdminOrder,
  type AdminProduct,
  type AdminUser,
  useAdminAnalyticsTyped,
  useAdminOrdersTyped,
  useAdminProductsTyped,
  useAdminUsersTyped,
} from "./useAdminApi";
// Leaderboard
export { useLeaderboardTyped } from "./useLeaderboardApi";
// Orders
export { useOrdersTyped } from "./useOrdersApi";
// Products
export { useProductsTyped } from "./useProductsApi";
// Profile
export { useProfileTyped } from "./useProfileApi";
// Support (Reviews, Tickets, AI Chat, Promo)
export { useAIChatTyped, usePromoTyped, useReviewsTyped, useSupportTyped } from "./useSupportApi";
