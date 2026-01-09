/**
 * PVNDORA Component Types
 * 
 * TypeScript definitions for the new frontend components.
 * These types define the data shape expected by UI components.
 */

import type { CurrencyCode } from '../utils/currency';

// ==================== CATALOG / PRODUCTS ====================

export type ProductAvailability = 'available' | 'on_demand' | 'discontinued' | 'coming_soon';

export interface CatalogProduct {
  id: string;
  name: string;
  categories?: string[]; // text/video/image/code/audio...
  category: string;      // legacy single category (kept for compatibility)
  price: number;
  final_price?: number;  // Price after discount (from API)
  msrp?: number;
  currency: string;      // Currency code (USD, RUB, etc.)
  description: string;
  warranty: number; // in hours
  duration?: number; // in days
  instructions?: string;
  image: string;
  popular: boolean;
  stock: number;
  fulfillment: number; // hours for preorder, 0 for instant
  sold: number; // sales_count
  video?: string; // Video URL for looped product visualization
  sku: string;
  version?: string;
  status: ProductAvailability; // derived from API status + stock
  can_fulfill_on_demand: boolean;
}

export interface ProductDetailData extends CatalogProduct {
  reviews: ProductReview[];
  files: ProductFile[];
  relatedProducts: CatalogProduct[];
}

export interface ProductFile {
  name: string;
  size: string;
  type: 'key' | 'doc' | 'config' | 'net';
}

export interface ProductReview {
  id: string | number;
  user: string;
  rating: number;
  date: string;
  text: string;
  verified: boolean;
}

// ==================== ORDERS ====================

export type OrderStatus = 'paid' | 'processing' | 'refunded';
export type OrderItemStatus = 'delivered' | 'waiting' | 'cancelled';

// Raw backend status for detailed UI rendering
export type RawOrderStatus = 
  | 'pending'     // Not paid yet
  | 'paid'        // Paid, stock available
  | 'prepaid'     // Paid, waiting for stock
  | 'partial'     // Some items delivered
  | 'delivered'   // All items delivered
  | 'cancelled'   // Cancelled
  | 'refunded';   // Refunded

export interface OrderItem {
  id: string;
  name: string;
  type: 'instant' | 'preorder';
  status: OrderItemStatus;
  credentials?: string | null;  // The delivered account/key data
  instructions?: string | null; // Instructions for using the product
  expiry?: string | null;
  hasReview: boolean;
  estimatedDelivery?: string | null;
  progress?: number | null;
  deadline?: string | null;
  reason?: string | null;
  orderRawStatus?: RawOrderStatus; // Parent order status for conditional rendering
  deliveredAt?: string | null; // When this specific item was delivered
  canRequestRefund?: boolean; // Can request refund for this specific item (within warranty)
  warrantyUntil?: string | null; // Warranty end date for this specific item
}

export interface Order {
  id: string;          // Full UUID for API operations
  displayId: string;   // Short ID for UI display (8 chars)
  date: string;
  total: number;
  currency: string;    // Currency code (USD, RUB, etc.)
  status: OrderStatus;
  items: OrderItem[];
  payment_url?: string | null; // Payment URL for pending orders
  payment_id?: string | null; // Invoice ID for checking payment status
  payment_gateway?: string | null; // Gateway name (crystalpay)
  deadline?: string | null;    // Payment deadline for pending orders (ISO string or formatted)

  // Extended status info for better UX
  rawStatus: RawOrderStatus;       // Backend status as-is
  paymentConfirmed: boolean;       // Is payment received?
  statusMessage: string;           // Human-readable status explanation
  canCancel: boolean;              // Can user cancel this order?
  canRequestRefund: boolean;       // Can user request refund?
}

// ==================== PROFILE ====================

export interface CareerLevel {
  id: number;
  label: string;
  min: number;
  max: number;
  color: string;
}

export interface NetworkNode {
  id: string | number;
  name?: string;
  handle: string;
  status: 'active' | 'inactive' | 'VIP' | 'SLEEP' | 'ACTIVE';
  earned: number;
  ordersCount: number;
  line?: 1 | 2 | 3;
  rank?: string;
  volume?: number;
  profit?: number;
  subs?: number;
  signal?: number;
  lastActive?: string;
  invitedBy?: string | null;
  activityData?: number[];
  photoUrl?: string;
}

export interface BillingLog {
  id: string;
  type: 'INCOME' | 'OUTCOME' | 'SYSTEM';
  source: string;
  amount: string;
  date: string;
  transactionType?: string;  // For localization: topup, purchase, refund, etc.
}

export interface ProfileStats {
  referrals: number;
  clicks: number;
  conversion: number;
  turnover: number;
}

export interface CareerProgress {
  currentTurnover: number;
  currentLevel: CareerLevel;
  nextLevel?: CareerLevel;
  progressPercent: number;
  thresholds?: { level2: number; level3: number };  // USD thresholds for level progression
  commissions?: { level1: number; level2: number; level3: number };  // Commission percentages per level
}

export interface ProfileData {
  name: string;
  handle: string;
  id: string;
  balance: number;  // Converted to user currency (for display)
  balanceUsd: number;  // Base USD amount (for frontend conversion)
  balanceCurrency?: string;  // Currency of user's actual balance (RUB, USD, etc.) - CRITICAL for withdrawals
  earnedRef: number;  // Converted
  earnedRefUsd: number;  // USD amount
  saved: number;  // Converted
  savedUsd: number;  // USD amount
  role: 'USER' | 'VIP' | 'ADMIN';
  isVip: boolean;
  partnerMode: 'commission' | 'discount';  // Partner reward mode
  partnerDiscountPercent: number;  // Discount given to referrals (in discount mode)
  referralLink: string;
  stats: ProfileStats;
  career: CareerProgress;
  networkTree: NetworkNode[];
  billingLogs: BillingLog[];
  currency: CurrencyCode;
  language: string;
  interfaceLanguage?: string; // User's preferred interface language (ru, en, etc.)
  photoUrl?: string;
  exchangeRate?: number;  // Exchange rate for frontend conversion (1 USD = X currency)
}

// ==================== LEADERBOARD ====================

export interface LeaderboardUser {
  rank: number;
  name: string;
  handle: string;
  marketSpend: number;
  actualSpend: number;
  saved: number;
  modules: number;
  trend: 'up' | 'down' | 'same';
  status: 'ONLINE' | 'AWAY' | 'BUSY';
  isMe: boolean;
  avatarUrl?: string;
  currency?: string; // Currency code (USD, RUB, etc.)
}

// ==================== CART / CHECKOUT ====================

export interface CartItem {
  id: string;
  name: string;
  category: string;
  price: number;        // Display price (in user's currency)
  priceUsd?: number;    // USD price (for calculations)
  currency: string;
  quantity: number;
  image: string;
}

export interface CartData {
  items: CartItem[];
  total: number;
  originalTotal: number;
  discountTotal: number;
  currency: string;
  exchangeRate?: number;
  // Base USD amounts for safe comparisons
  totalUsd?: number;
  originalTotalUsd?: number;
  discountTotalUsd?: number;
  promoCode?: string;
  promoDiscountPercent?: number;
}

export type PaymentMethod = 'internal' | 'crystalpay';

// ==================== SUPPORT ====================

export interface ChatMessage {
  id: string;
  sender: 'user' | 'agent';
  text: string;
  timestamp: string;
}

// ==================== NAVIGATION ====================

export type ViewType = 
  | 'home'
  | 'catalog'
  | 'product'
  | 'orders'
  | 'profile'
  | 'leaderboard'
  | 'admin'
  | 'legal';

export type NavigationTarget = 
  | ViewType 
  | { type: 'product'; product: CatalogProduct };


