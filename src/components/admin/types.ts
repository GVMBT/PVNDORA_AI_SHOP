/**
 * Admin Panel Types
 * 
 * Shared type definitions for admin components.
 */

export interface ProductData {
  id: string | number;
  name: string;
  category: string;
  description: string;
  price: number;
  msrp: number;
  type: string;
  stock: number;
  fulfillment: number;
  warranty: number;
  duration: number;
  sold: number;
  vpn: boolean;
  image: string;
  video?: string; // Video URL for looped product visualization
  instructions: string;
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
  source_channel?: 'main' | 'discount' | 'webapp';  // Order source channel
}

export interface UserData {
  id: number;
  username: string;
  role: 'USER' | 'VIP' | 'ADMIN';
  joinedAt: string;
  purchases: number;
  spent: number;
  balance: number;
  isBanned: boolean;
  invites: number;
  earned: number;
  savings: number;
  handle?: string;
  level?: 'ARCHITECT' | 'PROXY';
  rewardType?: 'commission' | 'discount';
  status?: string;
}

export interface TicketData {
  id: string;
  user: string;
  subject: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED' | 'APPROVED' | 'REJECTED' | 'CLOSED';
  createdAt: string;
  lastMessage: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
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
  status: 'pending' | 'processing' | 'completed' | 'rejected';
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

export type AdminView = 'dashboard' | 'catalog' | 'sales' | 'users' | 'partners' | 'support' | 'promo' | 'migration' | 'accounting' | 'withdrawals';







