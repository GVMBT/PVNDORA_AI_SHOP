/**
 * Admin Panel Types
 *
 * Shared type definitions for admin components.
 */

export interface ProductData {
  id: string | number;
  name: string;
  description: string;

  // Category (maps to `type` in DB)
  category: string; // ai, dev, design, music

  // Pricing
  price: number; // Base price (USD)
  prices?: Record<string, number>; // Anchor prices: {RUB: 990, USD: 10.50}
  msrp: number; // Strike-through price (shown if > price) - Base USD MSRP
  msrp_prices?: Record<string, number>; // Anchor MSRP prices: {RUB: 1290, USD: 250}
  discountPrice?: number; // Price for discount channel
  costPrice?: number; // Cost for accounting

  // Fulfillment
  fulfillmentType?: string; // 'auto' (from stock_items) or 'manual'
  fulfillment: number; // fulfillment_time_hours (for on-demand orders)

  // Product Settings
  warranty: number; // warranty_hours
  duration: number; // duration_days
  status?: string; // active, inactive, discontinued

  // Stock (read-only, calculated from stock_items)
  stock: number;
  sold: number;

  // Media
  image: string; // image_url
  video?: string;

  // Content
  instructions: string;

  // Timestamps
  created_at?: string;
}

export interface OrderData {
  id: string;
  user: string;
  product: string;
  amount: number;
  status: string;
  date: string;
  method: string;
  payment_id?: string;
  payment_gateway?: string;
  expires_at?: string;
  source_channel?: "main" | "discount" | "webapp"; // Order source channel
}

export interface UserData {
  id: number; // Telegram ID (for display)
  dbId: string; // Database UUID (for API calls)
  username: string;
  role: "USER" | "VIP" | "ADMIN";
  joinedAt: string;
  purchases: number;
  spent: number;
  balance: number;
  balanceCurrency: string; // User's balance currency (RUB, USD, etc.)
  isBanned: boolean;
  invites: number;
  earned: number;
  savings: number;
  handle?: string;
  level?: "ARCHITECT" | "PROXY";
  rewardType?: "commission" | "discount";
  status?: string;
}

export interface TicketData {
  id: string;
  user: string;
  subject: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "APPROVED" | "REJECTED" | "CLOSED";
  createdAt: string;
  lastMessage: string;
  priority: "LOW" | "MEDIUM" | "HIGH";
  date?: string;
  issue_type?: string; // replacement, refund, technical_issue, other
  item_id?: string; // Specific order item ID for item-level issues
  order_id?: string; // Related order ID
  telegram_id?: number; // User Telegram ID for direct contact
  admin_comment?: string; // Admin response/comment
  description?: string; // Issue description
  // Credentials for admin verification
  credentials?: string; // delivery_content from order_items
  product_name?: string; // Product name for context
}

export interface AdminStats {
  totalRevenue: number;
  ordersToday: number;
  ordersWeek: number;
  ordersMonth: number;
  totalUsers: number;
  pendingOrders: number;
  openTickets?: number;
  revenueByDay?: { date: string; amount: number }[];
  // Liabilities metrics
  totalUserBalances?: number;
  pendingWithdrawals?: number;
}

export interface WithdrawalData {
  id: string;
  user_id: string;
  amount: number;
  status: "pending" | "processing" | "completed" | "rejected";
  payment_method: string;
  payment_details: { details?: string } | null;
  admin_comment?: string | null;
  created_at: string;
  processed_at?: string | null;
  processed_by?: string | null;
  // Extended fields from join
  username?: string;
  first_name?: string;
  telegram_id?: number;
  user_balance?: number;
}

export type AdminView =
  | "dashboard"
  | "catalog"
  | "sales"
  | "users"
  | "partners"
  | "support"
  | "promo"
  | "migration"
  | "accounting"
  | "withdrawals";
