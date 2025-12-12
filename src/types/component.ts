/**
 * PVNDORA Component Types
 * 
 * TypeScript definitions for the new frontend components.
 * These types define the data shape expected by UI components.
 */

// ==================== CATALOG / PRODUCTS ====================

export type ProductAvailability = 'available' | 'on_demand' | 'discontinued' | 'coming_soon';

export interface CatalogProduct {
  id: string;
  name: string;
  categories?: string[]; // text/video/image/code/audio...
  category: string;      // legacy single category (kept for compatibility)
  price: number;
  msrp?: number;
  description: string;
  warranty: number; // in hours
  duration?: number; // in days
  instructions?: string;
  image: string;
  popular: boolean;
  stock: number;
  fulfillment: number; // hours for preorder, 0 for instant
  sold: number; // sales_count
  video?: string;
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
}

export interface Order {
  id: string;
  date: string;
  total: number;
  status: OrderStatus;
  items: OrderItem[];
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
  id: string;
  name: string;
  handle: string;
  status: 'active' | 'inactive';
  earned: number;
  ordersCount: number;
}

export interface BillingLog {
  id: string;
  type: 'INCOME' | 'OUTCOME';
  source: string;
  amount: string;
  date: string;
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
}

export interface ProfileData {
  name: string;
  handle: string;
  id: string;
  balance: number;
  earnedRef: number;
  saved: number;
  role: 'USER' | 'VIP' | 'ADMIN';
  isVip: boolean;
  referralLink: string;
  stats: ProfileStats;
  career: CareerProgress;
  networkTree: NetworkNode[];
  billingLogs: BillingLog[];
  currency: string;
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
}

// ==================== CART / CHECKOUT ====================

export interface CartItem {
  id: string;
  name: string;
  category: string;
  price: number;
  quantity: number;
  image: string;
}

export interface CartData {
  items: CartItem[];
  total: number;
  originalTotal: number;
  discountTotal: number;
  promoCode?: string;
  promoDiscountPercent?: number;
}

export type PaymentMethod = 'internal' | 'rukassa' | 'crystalpay';

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


