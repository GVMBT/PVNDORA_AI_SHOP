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
  | 'paid'
  | 'prepaid' 
  | 'partial'
  | 'delivered' 
  | 'cancelled' 
  | 'refunded';

export type ProductType = 'shared' | 'personal';
export type ProductStatus = 'active' | 'discontinued' | 'coming_soon' | 'out_of_stock';

// ==================== PRODUCTS ====================

export interface APIProduct {
  id: UUID;
  name: string;
  description: string;
  image_url?: string;
  video_url?: string; // Video background URL
  logo_svg_url?: string; // SVG logo (deprecated, use video_url instead)
  original_price: number; // Display price in user's currency
  price: number; // Display price in user's currency
  price_usd: number; // Base USD price (for backend calculations only)
  msrp?: number;
  currency: string; // User's currency code
  exchange_rate?: number; // Current exchange rate (1 USD = X currency)
  discount_percent: number;
  final_price: number; // Final price after discounts (in user's currency)
  final_price_usd?: number; // Final price in USD (for backend)
  is_anchor_price?: boolean; // True if price is fixed (won't change with exchange rate)
  warranty_days: number;
  duration_days?: number;
  available_count: number;
  available: boolean;
  can_fulfill_on_demand: boolean;
  fulfillment_time_hours?: number;
  type: ProductType;
  status: ProductStatus;
  instructions?: string;
  instruction_files?: Array<{ name: string; url: string; description?: string }>;
  rating: number;
  reviews_count: number;
  sales_count: number;
  categories?: string[]; // e.g. ["text","code"]
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
  count?: number;
  currency?: string; // Currency code for price display
  exchange_rate?: number; // Current exchange rate (1 USD = X currency)
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
  quantity?: number;
  price?: number;
  discount_percent?: number;
  status: OrderStatus;
  fulfillment_type: 'instant' | 'preorder';
  // Delivery data (from backend)
  delivery_content?: string;  // The account credentials/key
  delivery_instructions?: string;  // Instructions for using the product
  // Aliases for compatibility
  credentials?: string;
  expires_at?: string;
  delivered_at?: string;
  created_at?: string;
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
  order_type?: 'instant' | 'prepaid';
  created_at: string;
  expires_at?: string;           // Payment deadline (for pending orders)
  fulfillment_deadline?: string; // Delivery deadline (for prepaid orders)
  delivered_at?: string;         // When goods were delivered
  warranty_until?: string;       // Warranty end date
  payment_url?: string;
  payment_id?: string;            // Invoice ID from payment gateway (for checking status)
  payment_gateway?: string;       // crystalpay, rukassa, etc. (for checking status)
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
  payment_method?: 'card' | 'sbp' | 'crypto' | 'balance';
  payment_gateway?: 'crystalpay';
  use_cart?: boolean;
}

export interface APICreateOrderResponse {
  order_id: UUID;
  amount: number;
  original_price: number;
  discount_percent: number;
  payment_url?: string | null;  // Optional - null for balance payments, URL for external gateways
  payment_method: string;
}

// ==================== PROFILE ====================

export interface APIProfile {
  balance: number;  // Converted to user currency (for backward compatibility)
  balance_usd: number;  // Base USD amount (for frontend conversion)
  total_referral_earnings: number;  // Converted
  total_referral_earnings_usd: number;  // USD amount
  total_saved: number;  // Converted
  total_saved_usd: number;  // USD amount
  referral_link: string;
  created_at: string;
  is_admin: boolean;
  is_partner: boolean;
  currency: string;
  interface_language?: string;  // User's preferred interface language (ru, en, etc.)
  // User identity (for web login where initData not available)
  first_name?: string;
  username?: string;
  telegram_id?: number;
  photo_url?: string;
}

export interface APIReferralProgram {
  unlocked: boolean;
  status: 'locked' | 'active';
  is_partner: boolean;
  partner_mode: 'commission' | 'discount';  // Partner reward mode
  partner_discount_percent: number;  // Discount % given to referrals in discount mode
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

export interface APIBalanceTransaction {
  id: UUID;
  user_id: UUID;
  type: 'topup' | 'purchase' | 'refund' | 'bonus' | 'withdrawal' | 'cashback' | 'credit' | 'debit';
  amount: number;
  currency: string;
  balance_before: number;
  balance_after: number;
  reference_type?: string;  // 'order', 'payment', 'referral', etc.
  reference_id?: string;
  description?: string;
  status: 'pending' | 'completed' | 'failed' | 'cancelled';
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface APIProfileResponse {
  profile: APIProfile;
  referral_program: APIReferralProgram;
  referral_stats: APIReferralStats;
  bonus_history: APIBonusHistoryItem[];
  withdrawals: APIWithdrawalRequest[];
  balance_transactions?: APIBalanceTransaction[];
  currency: string;
  exchange_rate: number;  // Exchange rate for frontend conversion (1 USD = X currency)
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
  photo_url?: string;
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
  telegram_id?: number;
  photo_url?: string;
  modules_count?: number; // Count of delivered orders
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
  // Optional display fields
  final_price?: number;
  currency?: string;
  image_url?: string;
  // Base USD amounts for safe calculations
  unit_price_usd?: number;
  final_price_usd?: number;
  total_price_usd?: number;
}

export interface APICart {
  user_telegram_id?: number;
  created_at?: string;
  updated_at?: string;
}

export interface APICartResponse {
  cart: APICart;
  items: APICartItem[];
  total: number;
  subtotal: number;
  instant_total: number;
  prepaid_total: number;
  promo_code?: string;
  promo_discount_percent?: number;
  currency: string;
  exchange_rate?: number; // 1 USD = X currency
  // Display values (for UI, in user's currency)
  original_total?: number;
  // Base USD mirrors
  total_usd?: number;
  subtotal_usd?: number;
  original_total_usd?: number;
  instant_total_usd?: number;
  prepaid_total_usd?: number;
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

