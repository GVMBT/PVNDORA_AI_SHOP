/**
 * PVNDORA Typed API Hooks
 *
 * Re-exports all type-safe API hooks from domain-specific files.
 * Use CartContext (from contexts/CartContext.tsx) for cart operations.
 */

// Re-export all hooks from api/ folder
export { useProductsTyped } from "./api/useProductsApi";
export { useOrdersTyped } from "./api/useOrdersApi";
export { useProfileTyped } from "./api/useProfileApi";
export { useLeaderboardTyped } from "./api/useLeaderboardApi";
export {
  useReviewsTyped,
  useSupportTyped,
  useAIChatTyped,
  usePromoTyped,
} from "./api/useSupportApi";
export {
  useAdminProductsTyped,
  useAdminOrdersTyped,
  useAdminUsersTyped,
  useAdminAnalyticsTyped,
  type AdminProduct,
  type AdminOrder,
  type AdminUser,
  type AdminAnalytics,
} from "./api/useAdminApi";

// Note: useCartTyped has been removed.
// Use useCart from '../contexts/CartContext' instead for cart operations.
// This eliminates duplicate cart state management.
