/**
 * PVNDORA API Types
 * 
 * TypeScript definitions matching the backend API contracts.
 * These types are the source of truth for API communication.
 */

// ==================== COMMON ====================

export type UUID = string;
export type OrderStatus = 
  | 'pending' 
  | 'prepaid' 
  | 'fulfilling' 
  | 'ready' 
  | 'delivered' 
  | 'cancelled' 
  | 'refunded' 
  | 'failed'
  | 'payment_pending'
  | 'awaiting_payment';

export type ProductType = 'shared' | 'personal';
export type ProductStatus = 'active' | 'discontinued' | 'coming_soon' | 'out_of_stock';

// ==================== PRODUCTS ====================

export interface APIProduct {
  id: UUID;
  name: string;
  description: string;
  original_price: number;
  price: number;
  price_usd: number;
  msrp?: number;
  currency: string;
  discount_percent: number;
  final_price: number;
  warranty_days: number;
  duration_days?: number;
  available_count: number;
  available: boolean;
  can_fulfill_on_demand: boolean;
  fulfillment_time_hours?: number;
  type: ProductType;
  instructions?: string;
  instruction_files?: Array<{ name: string; url: string; description?: string }>;
  rating: number;
  reviews_count: number;
  sales_count: number;
}

export interface APIProductDetailed extends APIProduct {
  social_proof: {
    rating: number;
    review_count: number;
    sales_count: number;
    recent_reviews: Array<{
      rating: number;
      text?: string;
      created_at: string;
    }>;
  };
}

export interface APIProductsResponse {
  products: APIProduct[];
  count: number;
}

export interface APIProductResponse {
  product: APIProductDetailed;
  social_proof: APIProductDetailed['social_proof'];
}

// ==================== ORDERS ====================

export interface APIOrderItem {
  id: UUID;
  product_id: UUID;
  product_name: string;
  quantity: number;
  price: number;
  discount_percent: number;
  status: OrderStatus;
  fulfillment_type: 'instant' | 'preorder';
  credentials?: string;
  expires_at?: string;
  instructions?: string;
  has_review?: boolean;
}

export interface APIOrder {
  id: UUID;
  product_id: UUID;
  product_name: string;
  amount: number;
  amount_display: number;
  original_price?: number;
  original_price_display?: number;
  discount_percent: number;
  status: OrderStatus;
  created_at: string;
  expires_at?: string;
  payment_url?: string;
  items?: APIOrderItem[];
  currency: string;
}

export interface APIOrdersResponse {
  orders: APIOrder[];
  count: number;
  currency: string;
}

export interface APICreateOrderRequest {
  product_id?: UUID;
  quantity?: number;
  promo_code?: string;
  payment_method?: 'card' | 'sbp' | 'crypto';
  payment_gateway?: 'rukassa' | 'crystalpay' | '1plat' | 'freekassa';
  use_cart?: boolean;
}

export interface APICreateOrderResponse {
  order_id: UUID;
  amount: number;
  original_price: number;
  discount_percent: number;
  payment_url: string;
  payment_method: string;
}

// ==================== PROFILE ====================

export interface APIProfile {
  balance: number;
  total_referral_earnings: number;
  total_saved: number;
  referral_link: string;
  created_at: string;
  is_admin: boolean;
  is_partner: boolean;
  currency: string;
}

export interface APIReferralProgram {
  unlocked: boolean;
  status: 'locked' | 'active';
  is_partner: boolean;
  effective_level: number; // 0, 1, 2, 3
  level1_unlocked: boolean;
  level2_unlocked: boolean;
  level3_unlocked: boolean;
  turnover_usd: number;
  amount_to_level2_usd: number;
  amount_to_level3_usd: number;
  amount_to_next_level_usd: number;
  next_threshold_usd: number | null;
  thresholds_usd: {
    level2: number;
    level3: number;
  };
  commissions_percent: {
    level1: number;
    level2: number;
    level3: number;
  };
  level1_unlocked_at?: string;
  level2_unlocked_at?: string;
  level3_unlocked_at?: string;
}

export interface APIReferralStats {
  level1_count: number;
  level2_count: number;
  level3_count: number;
  level1_earnings: number;
  level2_earnings: number;
  level3_earnings: number;
  active_referrals: number;
  click_count: number;
  conversion_rate: number;
}

export interface APIBonusHistoryItem {
  id: UUID;
  amount: number;
  level: number;
  from_user_id?: UUID;
  order_id?: UUID;
  created_at: string;
  eligible: boolean;
}

export interface APIWithdrawalRequest {
  id: UUID;
  amount: number;
  payment_method: 'card' | 'phone' | 'crypto';
  payment_details: Record<string, string>;
  status: 'pending' | 'approved' | 'rejected' | 'completed';
  created_at: string;
}

export interface APIProfileResponse {
  profile: APIProfile;
  referral_program: APIReferralProgram;
  referral_stats: APIReferralStats;
  bonus_history: APIBonusHistoryItem[];
  withdrawals: APIWithdrawalRequest[];
  currency: string;
}

// ==================== REFERRAL NETWORK ====================

export interface APIReferralNode {
  id: UUID;
  telegram_id: number;
  username?: string;
  first_name?: string;
  created_at: string;
  is_active: boolean;
  order_count: number;
  earnings_generated: number;
}

export interface APIReferralNetworkResponse {
  referrals: APIReferralNode[];
  total: number;
  level: 1 | 2 | 3;
  offset: number;
  limit: number;
}

// ==================== LEADERBOARD ====================

export interface APILeaderboardEntry {
  rank: number;
  name: string;
  total_saved: number;
  is_current_user: boolean;
}

export interface APILeaderboardResponse {
  leaderboard: APILeaderboardEntry[];
  user_rank: number;
  user_saved: number;
}

// ==================== CART ====================

export interface APICartItem {
  product_id: UUID;
  product_name: string;
  quantity: number;
  instant_quantity: number;
  prepaid_quantity: number;
  unit_price: number;
  discount_percent: number;
  total_price: number;
}

export interface APICart {
  items: APICartItem[];
  total: number;
  original_total: number;
  discount_total: number;
  promo_code?: string;
  promo_discount_percent?: number;
}

export interface APICartResponse {
  cart: APICart;
}

// ==================== PAYMENT ====================

export interface APIPaymentMethod {
  system_group: string;
  name: string;
  icon: string;
  enabled: boolean;
  min_amount: number;
}

export interface APIPaymentMethodsResponse {
  systems: APIPaymentMethod[];
}

// ==================== REVIEWS ====================

export interface APIReviewRequest {
  order_id: UUID;
  rating: number;
  text?: string;
}

export interface APIReviewResponse {
  success: boolean;
  review_id?: UUID;
}

// ==================== TELEGRAM USER ====================

export interface TelegramUser {
  id: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  language_code?: string;
  is_premium?: boolean;
  photo_url?: string;
}

