/**
 * PVNDORA Typed API Hooks
 *
 * Re-exports all type-safe API hooks from domain-specific files.
 * Use CartContext (from contexts/CartContext.tsx) for cart operations.
 */

export {
  type AdminAnalytics,
  type AdminOrder,
  type AdminProduct,
  type AdminUser,
  useAdminAnalyticsTyped,
  useAdminOrdersTyped,
  useAdminProductsTyped,
  useAdminUsersTyped,
} from "./api/useAdminApi";
export { useLeaderboardTyped } from "./api/useLeaderboardApi";
export { useOrdersTyped } from "./api/useOrdersApi";
// Re-export all hooks from api/ folder
export { useProductsTyped } from "./api/useProductsApi";
export { useProfileTyped } from "./api/useProfileApi";
export {
  useAIChatTyped,
  usePromoTyped,
  useReviewsTyped,
  useSupportTyped,
} from "./api/useSupportApi";

// Note: useCartTyped has been removed.
// Use useCart from '../contexts/CartContext' instead for cart operations.
// This eliminates duplicate cart state management.
