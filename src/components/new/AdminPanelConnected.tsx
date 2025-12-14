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
import { formatRelativeTime, formatDate } from '../../utils/date';

interface AdminPanelConnectedProps {
  onExit: () => void;
}

const AdminPanelConnected: React.FC<AdminPanelConnectedProps> = ({ onExit }) => {
  const { products, getProducts, createProduct, updateProduct, deleteProduct, addStock, loading: productsLoading } = useAdminProductsTyped();
  const { orders, getOrders, loading: ordersLoading } = useAdminOrdersTyped();
  const { users, getUsers, updateUserRole, banUser, loading: usersLoading } = useAdminUsersTyped();
  const { analytics, getAnalytics, loading: analyticsLoading } = useAdminAnalyticsTyped();
  
  const [isInitialized, setIsInitialized] = useState(false);

  // Initial data fetch
  useEffect(() => {
    const init = async () => {
      await Promise.all([
        getProducts(),
        getOrders(undefined, 50),
        getUsers(50),
        getAnalytics()
      ]);
      setIsInitialized(true);
    };
    init();
  }, [getProducts, getOrders, getUsers, getAnalytics]);

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
  const transformedProducts = products.map(p => ({
    id: parseInt(p.id) || 0,
    name: p.name,
    category: p.category || 'Text',
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

  // Dashboard stats from analytics
  const transformedStats = analytics ? {
    totalRevenue: analytics.total_revenue || 0,
    ordersToday: analytics.orders_today || 0,
    ordersWeek: analytics.orders_this_week || 0,
    ordersMonth: analytics.orders_this_month || 0,
    activeUsers: analytics.active_users || 0
  } : undefined;

  return (
    <AdminPanel 
      onExit={onExit}
      // These props would need to be added to AdminPanel to use real data
      // For now, AdminPanel will use its internal mock data
      // TODO: Update AdminPanel to accept these props
      // products={transformedProducts}
      // orders={transformedOrders}
      // users={transformedUsers}
      // stats={transformedStats}
    />
  );
};

export default AdminPanelConnected;
