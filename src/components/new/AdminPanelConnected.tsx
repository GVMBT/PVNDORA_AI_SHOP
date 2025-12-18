/**
 * AdminPanelConnected
 * 
 * Connected version of AdminPanel with real API data.
 * Fetches products, orders, users, and analytics from backend.
 */

import React, { useEffect, useState, useCallback } from 'react';
import AdminPanel from './AdminPanel';
import { 
  useAdminProductsTyped, 
  useAdminOrdersTyped, 
  useAdminUsersTyped, 
  useAdminAnalyticsTyped,
  AdminProduct,
  AdminOrder,
  AdminUser,
  AdminAnalytics 
} from '../../hooks/useApiTyped';
import { useAdminPromoTyped, PromoCodeData } from '../../hooks/api/useAdminPromoApi';
import { useAdmin } from '../../hooks/useAdmin';
import { formatRelativeTime, formatDate } from '../../utils/date';
import { logger } from '../../utils/logger';
import type { TicketData } from '../admin/types';

interface AdminPanelConnectedProps {
  onExit: () => void;
}

const AdminPanelConnected: React.FC<AdminPanelConnectedProps> = ({ onExit }) => {
  const { products, getProducts, createProduct, updateProduct, deleteProduct, addStock, loading: productsLoading } = useAdminProductsTyped();
  const { orders, getOrders, loading: ordersLoading } = useAdminOrdersTyped();
  const { users, getUsers, updateUserRole, banUser, loading: usersLoading } = useAdminUsersTyped();
  const { analytics, getAnalytics, loading: analyticsLoading } = useAdminAnalyticsTyped();
  const { promoCodes, getPromoCodes, createPromoCode, updatePromoCode, deletePromoCode, togglePromoActive } = useAdminPromoTyped();
  const { getTickets } = useAdmin();
  
  const [isInitialized, setIsInitialized] = useState(false);
  const [tickets, setTickets] = useState<any[]>([]);

  // Fetch tickets
  const fetchTickets = useCallback(async () => {
    try {
      const response = await getTickets('all');
      if (response?.tickets) {
        setTickets(response.tickets);
      }
    } catch (err) {
      logger.error('Failed to fetch tickets', err);
      // Set empty array on error to prevent infinite loading
      setTickets([]);
    }
  }, [getTickets]);

  // Initial data fetch - only run once on mount
  useEffect(() => {
    let isMounted = true;
    
    const init = async () => {
      try {
        // Use Promise.allSettled to continue even if some requests fail
        const results = await Promise.allSettled([
          getProducts(),
          getOrders(undefined, 50),
          getUsers(50),
          getAnalytics(),
          getPromoCodes(),
          fetchTickets()
        ]);
        
        // Log any failures
        results.forEach((result, index) => {
          if (result.status === 'rejected') {
            const names = ['products', 'orders', 'users', 'analytics', 'promoCodes', 'tickets'];
            logger.error(`Failed to fetch ${names[index]}:`, result.reason);
          }
        });
        
        if (isMounted) {
          setIsInitialized(true);
        }
      } catch (err) {
        logger.error('Failed to initialize admin panel', err);
        // Set initialized even on error to prevent infinite loading
        if (isMounted) {
          setIsInitialized(true);
        }
      }
    };
    
    init();
    
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run only once on mount
  
  // Promo handlers
  const handleCreatePromo = useCallback(async (data: Omit<PromoCodeData, 'id' | 'usage_count' | 'created_at'>) => {
    await createPromoCode(data);
  }, [createPromoCode]);
  
  const handleUpdatePromo = useCallback(async (id: string, data: Partial<PromoCodeData>) => {
    await updatePromoCode(id, data);
  }, [updatePromoCode]);
  
  const handleDeletePromo = useCallback(async (id: string) => {
    await deletePromoCode(id);
  }, [deletePromoCode]);
  
  const handleTogglePromoActive = useCallback(async (id: string, isActive: boolean) => {
    await togglePromoActive(id, isActive);
  }, [togglePromoActive]);

  // Loading state
  if (!isInitialized) {
    return (
      <div className="fixed inset-0 z-[100] bg-[#050505] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Initializing Admin Terminal...
          </div>
        </div>
      </div>
    );
  }

  // Transform data to match AdminPanel expected format
  // Backend now returns properly mapped fields
  const transformedProducts = products.map(p => ({
    id: p.id,  // Keep as string (UUID)
    name: p.name,
    category: p.category || 'ai',
    description: p.description || '',
    price: p.price,
    msrp: p.msrp || p.price * 1.5,
    type: p.type === 'instant' ? 'Instant' : 'Preorder',
    stock: p.stock || 0,
    fulfillment: p.fulfillment || 0,
    warranty: p.warranty || 168,
    duration: p.duration || 30,
    sold: p.sold || 0,
    vpn: p.vpn || false,
    image: p.image || 'https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=800&auto=format&fit=crop',
    video: p.video,
    instructions: p.instructions || ''
  }));

  const transformedOrders = orders.map(o => ({
    id: o.id,
    user: o.user_handle || `@user_${o.user_id?.slice(0, 6)}`,
    product: o.product_name || 'Unknown Product',
    amount: o.amount,
    status: o.status?.toUpperCase() || 'PENDING',
    date: formatRelativeTime(o.created_at),
    method: o.payment_method?.toUpperCase() || 'UNKNOWN'
  }));

  const transformedUsers = users.map(u => ({
    id: parseInt(u.telegram_id) || 0,
    username: u.username || `user_${u.id?.slice(0, 6)}`,
    role: (u.role?.toUpperCase() || 'USER') as 'USER' | 'VIP' | 'ADMIN',
    joinedAt: formatDate(u.created_at),
    purchases: u.orders_count || 0,
    spent: u.total_spent || 0,
    balance: u.balance || 0,
    isBanned: u.is_banned || false,
    invites: 0, // TODO: Add to backend
    earned: 0, // TODO: Add to backend
    savings: 0 // TODO: Add to backend
  }));

  // Transform tickets
  const transformedTickets: TicketData[] = tickets.map((t: any) => ({
    id: t.id,
    user: t.first_name || t.username || `user_${t.user_id?.slice(0, 6)}`,
    subject: t.description?.slice(0, 50) || 'No subject',
    status: (t.status?.toUpperCase() || 'OPEN') as TicketData['status'],
    createdAt: t.created_at,
    lastMessage: t.description || '',
    priority: 'MEDIUM' as const,
    date: formatRelativeTime(t.created_at),
    issue_type: t.issue_type,
    item_id: t.item_id,
    order_id: t.order_id,
    telegram_id: t.telegram_id,
    admin_comment: t.admin_comment,
    description: t.description
  }));

  // Dashboard stats from analytics
  const transformedStats = analytics ? {
    totalRevenue: analytics.total_revenue || 0,
    ordersToday: analytics.orders_today || 0,
    ordersWeek: analytics.orders_this_week || 0,
    ordersMonth: analytics.orders_this_month || 0,
    activeUsers: analytics.active_users || 0,
    openTickets: analytics.open_tickets || 0,
    revenueByDay: analytics.revenue_by_day || [],
    // Liabilities metrics
    totalUserBalances: analytics.total_user_balances || 0,
    pendingWithdrawals: analytics.pending_withdrawals || 0
  } : undefined;

  return (
    <AdminPanel 
      onExit={onExit}
      products={transformedProducts}
      orders={transformedOrders}
      users={transformedUsers}
      tickets={transformedTickets}
      stats={transformedStats}
      promoCodes={promoCodes}
      onCreatePromo={handleCreatePromo}
      onUpdatePromo={handleUpdatePromo}
      onDeletePromo={handleDeletePromo}
      onTogglePromoActive={handleTogglePromoActive}
      onRefreshTickets={fetchTickets}
    />
  );
};

export default AdminPanelConnected;
