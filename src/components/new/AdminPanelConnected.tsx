/**
 * AdminPanelConnected
 * 
 * Connected version of AdminPanel with real API data.
 * All data transformations are memoized to prevent infinite re-renders.
 */

import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import AdminPanel from './AdminPanel';
import { 
  useAdminProductsTyped, 
  useAdminOrdersTyped, 
  useAdminUsersTyped, 
  useAdminAnalyticsTyped,
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
  // API hooks
  const { products, getProducts, deleteProduct } = useAdminProductsTyped();
  const { orders, getOrders } = useAdminOrdersTyped();
  const { users, getUsers, banUser, updateBalance } = useAdminUsersTyped();
  const { analytics, getAnalytics } = useAdminAnalyticsTyped();
  const { promoCodes, getPromoCodes, createPromoCode, updatePromoCode, deletePromoCode, togglePromoActive } = useAdminPromoTyped();
  const { getTickets } = useAdmin();
  
  // Local state
  const [isInitialized, setIsInitialized] = useState(false);
  const [tickets, setTickets] = useState<any[]>([]);
  
  // Ref to store user ID mapping (telegram_id -> UUID)
  const userIdMapRef = useRef<Map<number, string>>(new Map());

  // Fetch tickets - stable callback
  const fetchTickets = useCallback(async () => {
    try {
      const response = await getTickets('all');
      if (response?.tickets) {
        setTickets(response.tickets);
      }
    } catch (err) {
      logger.error('Failed to fetch tickets', err);
      setTickets([]);
    }
  }, [getTickets]);

  // Initial data fetch - only run once on mount
  useEffect(() => {
    let isMounted = true;
    
    const init = async () => {
      try {
        await Promise.allSettled([
          getProducts(),
          getOrders(undefined, 50),
          getUsers(50),
          getAnalytics(),
          getPromoCodes(),
          fetchTickets()
        ]);
        
        if (isMounted) {
          setIsInitialized(true);
        }
      } catch (err) {
        logger.error('Failed to initialize admin panel', err);
        if (isMounted) {
          setIsInitialized(true);
        }
      }
    };
    
    init();
    
    return () => { isMounted = false; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Memoized transformations
  const transformedProducts = useMemo(() => 
    products.map(p => ({
      id: p.id,
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
    }))
  , [products]);

  const transformedOrders = useMemo(() => 
    orders.map(o => ({
      id: o.id,
      user: o.user_handle || `@user_${o.user_id?.slice(0, 6)}`,
      product: o.product_name || 'Unknown Product',
      amount: o.amount,
      status: o.status?.toUpperCase() || 'PENDING',
      date: formatRelativeTime(o.created_at),
      method: o.payment_method?.toUpperCase() || 'UNKNOWN'
    }))
  , [orders]);

  const transformedUsers = useMemo(() => {
    // Update ref with fresh mapping
    const newMap = new Map<number, string>();
    const result = users.map(u => {
      const telegramId = parseInt(u.telegram_id) || 0;
      newMap.set(telegramId, u.id);
      return {
        id: telegramId,
        username: u.username || `user_${u.id?.slice(0, 6)}`,
        role: (u.role?.toUpperCase() || 'USER') as 'USER' | 'VIP' | 'ADMIN',
        joinedAt: formatDate(u.created_at),
        purchases: u.orders_count || 0,
        spent: u.total_spent || 0,
        balance: u.balance || 0,
        isBanned: u.is_banned || false,
        invites: 0,
        earned: 0,
        savings: 0
      };
    });
    userIdMapRef.current = newMap;
    return result;
  }, [users]);

  const transformedTickets = useMemo((): TicketData[] => 
    tickets.map((t: any) => ({
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
    }))
  , [tickets]);

  const transformedStats = useMemo(() => {
    if (!analytics) return undefined;
    return {
      totalRevenue: analytics.total_revenue || 0,
      ordersToday: analytics.orders_today || 0,
      ordersWeek: analytics.orders_this_week || 0,
      ordersMonth: analytics.orders_this_month || 0,
      totalUsers: (analytics as any).total_users || 0,
      pendingOrders: (analytics as any).pending_orders || 0,
      openTickets: (analytics as any).open_tickets || 0,
      revenueByDay: analytics.revenue_by_day || [],
      totalUserBalances: (analytics as any).total_user_balances || 0,
      pendingWithdrawals: (analytics as any).pending_withdrawals || 0
    };
  }, [analytics]);

  // Stable action handlers - use ref for userIdMap to avoid dependency issues
  const handleBanUser = useCallback((telegramId: number, ban: boolean) => {
    const userId = userIdMapRef.current.get(telegramId);
    if (userId) {
      banUser(userId, ban);
    }
  }, [banUser]);
  
  const handleUpdateBalance = useCallback((telegramId: number, _amount: number) => {
    const userId = userIdMapRef.current.get(telegramId);
    if (userId) {
      const amount = window.prompt('Enter amount to add (negative to subtract):', '0');
      if (amount !== null) {
        const parsed = parseFloat(amount);
        if (!isNaN(parsed)) {
          updateBalance(userId, parsed);
        }
      }
    }
  }, [updateBalance]);

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

  // Product handlers
  const handleDeleteProduct = useCallback(async (productId: string) => {
    await deleteProduct(productId);
  }, [deleteProduct]);

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
      onBanUser={handleBanUser}
      onUpdateBalance={handleUpdateBalance}
      onDeleteProduct={handleDeleteProduct}
    />
  );
};

export default AdminPanelConnected;
