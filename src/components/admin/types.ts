/**
 * Admin Panel Types
 * 
 * Shared type definitions for admin components.
 */

export interface ProductData {
  id: number;
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
  video?: string;
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
}

export interface AdminStats {
  totalRevenue: number;
  ordersToday: number;
  ordersWeek: number;
  ordersMonth: number;
  activeUsers: number;
  openTickets?: number;
  revenueByDay?: { date: string; amount: number }[];
}

export type AdminView = 'dashboard' | 'catalog' | 'sales' | 'partners' | 'support' | 'promo';







