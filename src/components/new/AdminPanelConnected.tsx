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
import type { AccountingData } from '../admin';

interface AdminPanelConnectedProps {
  onExit: () => void;
}

const AdminPanelConnected: React.FC<AdminPanelConnectedProps> = ({ onExit }) => {
  // API hooks
  const { products, getProducts, createProduct, updateProduct, deleteProduct } = useAdminProductsTyped();
  const { orders, getOrders } = useAdminOrdersTyped();
  const { users, getUsers, banUser, updateBalance } = useAdminUsersTyped();
  const { analytics, getAnalytics } = useAdminAnalyticsTyped();
  const { promoCodes, getPromoCodes, createPromoCode, updatePromoCode, deletePromoCode, togglePromoActive } = useAdminPromoTyped();
  const { getTickets, getWithdrawals } = useAdmin();
  
  // Local state
  const [isInitialized, setIsInitialized] = useState(false);
  const [tickets, setTickets] = useState<any[]>([]);
  const [withdrawals, setWithdrawals] = useState<any[]>([]);
  const [accountingData, setAccountingData] = useState<AccountingData | undefined>();
  const [isAccountingLoading, setIsAccountingLoading] = useState(false);
  
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

  // Fetch withdrawals - stable callback
  const fetchWithdrawals = useCallback(async () => {
    try {
      const response = await getWithdrawals('all');
      if (response?.withdrawals) {
        setWithdrawals(response.withdrawals);
      }
    } catch (err) {
      logger.error('Failed to fetch withdrawals', err);
      setWithdrawals([]);
    }
  }, [getWithdrawals]);

  // Fetch accounting data
  const fetchAccounting = useCallback(async () => {
    setIsAccountingLoading(true);
    try {
      const { apiRequest } = await import('../../utils/apiClient');
      const { API } = await import('../../config');
      const data = await apiRequest<any>(`${API.ADMIN_URL}/accounting/overview`);
      
      // Log for debugging
      logger.info('Accounting data loaded', data);
      
      setAccountingData({
          totalRevenue: parseFloat(data.total_revenue) || 0,
          revenueGross: parseFloat(data.total_revenue_gross) || 0,
          revenueThisMonth: parseFloat(data.revenue_this_month) || 0,
          revenueToday: parseFloat(data.revenue_today) || 0,
          totalCogs: parseFloat(data.total_cogs) || 0,
          totalAcquiringFees: parseFloat(data.total_acquiring_fees) || 0,
          totalReferralPayouts: parseFloat(data.total_referral_payouts) || 0,
          totalReserves: parseFloat(data.total_reserves) || 0,
          totalReviewCashbacks: parseFloat(data.total_review_cashbacks) || 0,
          totalReplacementCosts: parseFloat(data.total_replacement_costs) || 0,
          totalOtherExpenses: parseFloat(data.total_other_expenses) || 0,
          totalInsuranceRevenue: parseFloat(data.total_insurance_revenue) || 0,
          totalDiscountsGiven: parseFloat(data.total_discounts_given) || 0,
          totalUserBalances: parseFloat(data.total_user_balances) || 0,
          pendingWithdrawals: parseFloat(data.pending_withdrawals) || 0,
          netProfit: parseFloat(data.net_profit) || 0,
          totalOrders: parseInt(data.total_orders) || 0,
          ordersThisMonth: parseInt(data.orders_this_month) || 0,
          ordersToday: parseInt(data.orders_today) || 0,
          // Reserve tracking
          reservesUsed: parseFloat(data.reserves_used) || 0,
          reservesAvailable: parseFloat(data.reserves_available) || 0,
          // Currency breakdown
          currencyBreakdown: data.currency_breakdown || {},
        });
    } catch (err) {
      logger.error('Failed to fetch accounting data', err);
    } finally {
      setIsAccountingLoading(false);
    }
  }, []);

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
          fetchTickets(),
          fetchWithdrawals(),
          fetchAccounting()
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

  // ALL useMemo hooks MUST be before any conditional returns (Rules of Hooks)
  
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
        balanceCurrency: u.balance_currency || 'USD',
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
      description: t.description,
      // Credentials for admin verification
      credentials: t.credentials,
      product_name: t.product_name
    }))
  , [tickets]);

  // Transform withdrawals for admin panel - MUST be before conditional return
  const transformedWithdrawals = useMemo(() => 
    withdrawals.map((w: any) => ({
      id: w.id,
      user_id: w.user_id,
      telegram_id: w.telegram_id,
      username: w.username,
      first_name: w.first_name,
      amount: w.amount || 0,
      payment_method: w.payment_method,
      payment_details: w.payment_details,
      status: w.status || 'pending',
      admin_comment: w.admin_comment,
      created_at: w.created_at,
      processed_at: w.processed_at,
      user_balance: w.user_balance
    }))
  , [withdrawals]);

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
  const handleSaveProduct = useCallback(async (product: any) => {
    if (product.id) {
      // Update existing product
      await updateProduct(product.id, product);
    } else {
      // Create new product
      await createProduct(product);
    }
  }, [createProduct, updateProduct]);

  const handleDeleteProduct = useCallback(async (productId: string) => {
    await deleteProduct(productId);
  }, [deleteProduct]);

  // Loading state - AFTER all hooks
  if (!isInitialized) {
    return (
      <div className="fixed inset-0 z-[100] bg-[#050505] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <div className="font-mono text-xs text-gray-500 uppercase tracking-widest">
            Загрузка админ-панели...
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
      withdrawals={transformedWithdrawals}
      stats={transformedStats}
      promoCodes={promoCodes}
      accountingData={accountingData}
      onCreatePromo={handleCreatePromo}
      onUpdatePromo={handleUpdatePromo}
      onDeletePromo={handleDeletePromo}
      onTogglePromoActive={handleTogglePromoActive}
      onRefreshTickets={fetchTickets}
      onRefreshWithdrawals={fetchWithdrawals}
      onRefreshAccounting={fetchAccounting}
      onRefreshOrders={getOrders}
      isAccountingLoading={isAccountingLoading}
      onBanUser={handleBanUser}
      onUpdateBalance={handleUpdateBalance}
      onSaveProduct={handleSaveProduct}
      onDeleteProduct={handleDeleteProduct}
    />
  );
};

export default AdminPanelConnected;
