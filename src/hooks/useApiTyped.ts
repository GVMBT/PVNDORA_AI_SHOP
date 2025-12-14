/**
 * PVNDORA Typed API Hooks
 * 
 * Type-safe API hooks with automatic data transformation.
 * These hooks wrap useApi and apply adapters for component consumption.
 */

import React, { useState, useCallback } from 'react';
import { useApi } from './useApi';
import type {
  APIProductsResponse,
  APIProductResponse,
  APIOrdersResponse,
  APIProfileResponse,
  APILeaderboardResponse,
  APICartResponse,
  APICreateOrderRequest,
  APICreateOrderResponse,
  APIReferralNetworkResponse,
} from '../types/api';
import type {
  CatalogProduct,
  ProductDetailData,
  Order,
  ProfileData,
  LeaderboardUser,
  CartData,
} from '../types/component';
import {
  adaptProduct,
  adaptProductList,
  adaptProductDetail,
  adaptOrders,
  adaptProfile,
  adaptReferralNetwork,
  adaptLeaderboard,
  adaptCart,
} from '../adapters';

/**
 * Get browser/Telegram language code
 */
function getLanguageCode(): string {
  const tgLang = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
  const browserLang = navigator.language?.split('-')[0];
  return tgLang || browserLang || 'en';
}

/**
 * Hook for fetching products with type safety
 */
export function useProductsTyped() {
  const { get, loading, error } = useApi();
  const [products, setProducts] = useState<CatalogProduct[]>([]);

  const getProducts = useCallback(async (category?: string): Promise<CatalogProduct[]> => {
    const lang = getLanguageCode();
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    params.append('language_code', lang);
    
    try {
      const response: APIProductsResponse = await get(`/products?${params.toString()}`);
      const adapted = adaptProductList(response.products);
      setProducts(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch products:', err);
      return [];
    }
  }, [get]);

  const getProduct = useCallback(async (id: string): Promise<ProductDetailData | null> => {
    const lang = getLanguageCode();
    try {
      const response: APIProductResponse = await get(`/products/${id}?language_code=${lang}`);
      return adaptProductDetail(response);
    } catch (err) {
      console.error(`Failed to fetch product ${id}:`, err);
      return null;
    }
  }, [get]);

  return { products, getProducts, getProduct, loading, error };
}

/**
 * Hook for fetching orders with type safety
 */
export function useOrdersTyped() {
  const { get, post, loading, error } = useApi();
  const [orders, setOrders] = useState<Order[]>([]);

  const getOrders = useCallback(async (params?: { limit?: number; offset?: number }): Promise<Order[]> => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.offset) searchParams.append('offset', params.offset.toString());
    const qs = searchParams.toString();
    
    try {
      const response: APIOrdersResponse = await get(`/orders${qs ? `?${qs}` : ''}`);
      const adapted = adaptOrders(response);
      setOrders(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch orders:', err);
      return [];
    }
  }, [get]);

  const createOrder = useCallback(async (request: APICreateOrderRequest): Promise<APICreateOrderResponse | null> => {
    try {
      return await post('/orders', request);
    } catch (err) {
      console.error('Failed to create order:', err);
      return null;
    }
  }, [post]);

  return { orders, getOrders, createOrder, loading, error };
}

/**
 * Hook for fetching profile with type safety
 */
export function useProfileTyped() {
  const { get, post, loading, error } = useApi();
  const [profile, setProfile] = useState<ProfileData | null>(null);

  const getProfile = useCallback(async (): Promise<ProfileData | null> => {
    try {
      const response: APIProfileResponse = await get('/profile');
      const telegramUser = (window as any).Telegram?.WebApp?.initDataUnsafe?.user;
      const adapted = adaptProfile(response, telegramUser);
      
      // Also fetch referral network for all 3 levels
      try {
        const [level1Res, level2Res, level3Res] = await Promise.all([
          get('/referral/network?level=1&limit=50'),
          get('/referral/network?level=2&limit=50'),
          get('/referral/network?level=3&limit=50'),
        ]) as [APIReferralNetworkResponse, APIReferralNetworkResponse, APIReferralNetworkResponse];
        
        adapted.networkTree = adaptReferralNetwork(
          level1Res.referrals || [],
          level2Res.referrals || [],
          level3Res.referrals || []
        );
      } catch (networkErr) {
        console.warn('Failed to fetch referral network, using empty tree:', networkErr);
        // Keep empty networkTree
      }
      
      setProfile(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch profile:', err);
      return null;
    }
  }, [get]);

  const requestWithdrawal = useCallback(async (
    amount: number,
    method: string,
    details: string
  ): Promise<{ success: boolean; message: string }> => {
    try {
      return await post('/profile/withdraw', { amount, method, details });
    } catch (err) {
      console.error('Failed to request withdrawal:', err);
      throw err;
    }
  }, [post]);

  const createShareLink = useCallback(async (): Promise<{ prepared_message_id: string }> => {
    try {
      return await post('/referral/share-link', {});
    } catch (err) {
      console.error('Failed to create share link:', err);
      throw err;
    }
  }, [post]);

  const createTopUp = useCallback(async (
    amount: number,
    currency: string = 'RUB'
  ): Promise<{ success: boolean; payment_url: string; topup_id: string; amount_rub: number }> => {
    try {
      return await post('/profile/topup', { amount, currency });
    } catch (err) {
      console.error('Failed to create top-up:', err);
      throw err;
    }
  }, [post]);

  return { profile, getProfile, requestWithdrawal, createShareLink, createTopUp, loading, error };
}

/**
 * Hook for fetching leaderboard with type safety and pagination
 */
export function useLeaderboardTyped() {
  const { get, loading, error } = useApi();
  const [leaderboard, setLeaderboard] = useState<LeaderboardUser[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [currentOffset, setCurrentOffset] = useState(0);
  // Track loaded offsets to prevent duplicate requests
  const loadedOffsetsRef = React.useRef<Set<number>>(new Set());

  const getLeaderboard = useCallback(async (limit: number = 15, offset: number = 0, append: boolean = false): Promise<LeaderboardUser[]> => {
    // Prevent duplicate requests for same offset
    if (append && loadedOffsetsRef.current.has(offset)) {
      console.log(`[Leaderboard] Skipping duplicate request for offset ${offset}`);
      return [];
    }
    
    try {
      const response: APILeaderboardResponse = await get(`/leaderboard?limit=${limit}&offset=${offset}`);
      const telegramUser = (window as any).Telegram?.WebApp?.initDataUnsafe?.user;
      const adapted = adaptLeaderboard(response, telegramUser?.id?.toString());
      
      // Mark this offset as loaded
      loadedOffsetsRef.current.add(offset);
      
      // Update pagination state
      const responseHasMore = (response as any).has_more;
      setHasMore(responseHasMore ?? adapted.length === limit);
      setCurrentOffset(offset + adapted.length);
      
      // Append with deduplication by rank
      if (append && offset > 0) {
        setLeaderboard(prev => {
          // Combine previous and new entries
          const combined = [...prev, ...adapted];
          // Deduplicate by rank - keep the first occurrence
          const seenRanks = new Set<number>();
          const unique = combined.filter(user => {
            if (seenRanks.has(user.rank)) {
              return false;
            }
            seenRanks.add(user.rank);
            return true;
          });
          // Sort by rank
          return unique.sort((a, b) => a.rank - b.rank);
        });
      } else {
        // Fresh load - reset tracking
        loadedOffsetsRef.current.clear();
        loadedOffsetsRef.current.add(offset);
        setLeaderboard(adapted);
      }
      
      return adapted;
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
      return [];
    }
  }, [get]);

  const loadMore = useCallback(async () => {
    if (!hasMore || loading) return;
    return getLeaderboard(15, currentOffset, true);
  }, [getLeaderboard, hasMore, loading, currentOffset]);

  // Reset function for when component unmounts/remounts
  const reset = useCallback(() => {
    loadedOffsetsRef.current.clear();
    setLeaderboard([]);
    setCurrentOffset(0);
    setHasMore(true);
  }, []);

  return { leaderboard, getLeaderboard, loadMore, hasMore, loading, error, reset };
}

/**
 * Hook for cart operations with type safety
 */
export function useCartTyped() {
  const { get, post, patch, del, loading, error } = useApi();
  const [cart, setCart] = useState<CartData | null>(null);

  const getCart = useCallback(async (): Promise<CartData | null> => {
    try {
      const response: APICartResponse = await get('/cart');
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch cart:', err);
      return null;
    }
  }, [get]);

  const addToCart = useCallback(async (productId: string, quantity = 1) => {
    try {
      // POST returns updated cart response directly
      const response: APICartResponse = await post('/cart/add', { product_id: productId, quantity });
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to add to cart:', err);
      throw err;
    }
  }, [post]);

  const updateCartItem = useCallback(async (productId: string, quantity: number) => {
    try {
      // PATCH returns updated cart response directly
      const response: APICartResponse = await patch('/cart/item', { product_id: productId, quantity });
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to update cart item:', err);
      throw err;
    }
  }, [patch]);

  const removeCartItem = useCallback(async (productId: string) => {
    try {
      // DELETE returns updated cart response directly
      const response: APICartResponse = await del(`/cart/item?product_id=${encodeURIComponent(productId)}`);
      const adapted = adaptCart(response);
      setCart(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to remove cart item:', err);
      throw err;
    }
  }, [del]);

  const applyPromo = useCallback(async (code: string) => {
    try {
      await post('/cart/promo/apply', { code });
      return getCart();
    } catch (err) {
      console.error('Failed to apply promo:', err);
      throw err;
    }
  }, [post, getCart]);

  const removePromo = useCallback(async () => {
    try {
      await post('/cart/promo/remove', {});
      return getCart();
    } catch (err) {
      console.error('Failed to remove promo:', err);
      throw err;
    }
  }, [post, getCart]);

  return {
    cart,
    getCart,
    addToCart,
    updateCartItem,
    removeCartItem,
    applyPromo,
    removePromo,
    loading,
    error,
  };
}

/**
 * Hook for reviews
 */
export function useReviewsTyped() {
  const { post, loading, error } = useApi();

  const submitReview = useCallback(async (
    orderId: string,
    rating: number,
    text?: string
  ): Promise<{ success: boolean; review_id?: string }> => {
    try {
      return await post('/reviews', { order_id: orderId, rating, text });
    } catch (err) {
      console.error('Failed to submit review:', err);
      throw err;
    }
  }, [post]);

  return { submitReview, loading, error };
}

/**
 * Support ticket interface
 */
interface SupportTicket {
  id: string;
  status: 'open' | 'approved' | 'rejected' | 'closed';
  issue_type: string;
  message: string;
  admin_reply?: string;
  order_id?: string;
  created_at: string;
}

/**
 * Hook for support tickets
 */
export function useSupportTyped() {
  const { get, post, loading, error } = useApi();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);

  const getTickets = useCallback(async (): Promise<SupportTicket[]> => {
    try {
      const response = await get('/support/tickets');
      const data = response.tickets || [];
      setTickets(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
      return [];
    }
  }, [get]);

  const createTicket = useCallback(async (
    message: string,
    issueType: string = 'general',
    orderId?: string
  ): Promise<{ success: boolean; ticket_id?: string; message?: string }> => {
    try {
      return await post('/support/tickets', {
        message,
        issue_type: issueType,
        order_id: orderId,
      });
    } catch (err) {
      console.error('Failed to create ticket:', err);
      throw err;
    }
  }, [post]);

  const getTicket = useCallback(async (ticketId: string): Promise<SupportTicket | null> => {
    try {
      const response = await get(`/support/tickets/${ticketId}`);
      return response.ticket || null;
    } catch (err) {
      console.error(`Failed to fetch ticket ${ticketId}:`, err);
      return null;
    }
  }, [get]);

  return { tickets, getTickets, createTicket, getTicket, loading, error };
}

/**
 * AI Chat response interface
 */
interface AIChatResponse {
  reply_text: string;
  action: string;
  thought?: string;
  ticket_id?: string;
  product_id?: string;
  total_amount?: number;
}

/**
 * Chat history item interface
 */
interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

/**
 * Hook for AI chat (powered by Gemini)
 */
export function useAIChatTyped() {
  const { get, post, del, loading, error } = useApi();
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);

  const sendMessage = useCallback(async (message: string): Promise<AIChatResponse | null> => {
    try {
      const response: AIChatResponse = await post('/ai/chat', { message });
      return response;
    } catch (err) {
      console.error('Failed to send AI message:', err);
      return null;
    }
  }, [post]);

  const getHistory = useCallback(async (limit: number = 20): Promise<ChatHistoryItem[]> => {
    try {
      const response = await get(`/ai/history?limit=${limit}`);
      const messages = response.messages || [];
      setHistory(messages);
      return messages;
    } catch (err) {
      console.error('Failed to get chat history:', err);
      return [];
    }
  }, [get]);

  const clearHistory = useCallback(async (): Promise<boolean> => {
    try {
      await del('/ai/history');
      setHistory([]);
      return true;
    } catch (err) {
      console.error('Failed to clear chat history:', err);
      return false;
    }
  }, [del]);

  return { history, sendMessage, getHistory, clearHistory, loading, error };
}

// ==================== ADMIN HOOKS ====================

/**
 * Admin product interface (extended with admin-specific fields)
 */
export interface AdminProduct {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  msrp: number;
  type: 'instant' | 'preorder';
  stock: number;
  fulfillment: number; // hours
  warranty: number; // hours
  duration: number; // days
  sold: number;
  status: 'active' | 'inactive' | 'discontinued';
  vpn: boolean;
  image?: string;
  video?: string;
  instructions?: string;
  created_at?: string;
}

/**
 * Admin order interface
 */
export interface AdminOrder {
  id: string;
  user_id: string;
  user_handle: string;
  product_name: string;
  amount: number;
  status: string;
  payment_method: string;
  created_at: string;
}

/**
 * Admin user interface
 */
export interface AdminUser {
  id: string;
  telegram_id: string;
  username: string;
  role: string;
  balance: number;
  total_spent: number;
  orders_count: number;
  is_banned: boolean;
  created_at: string;
}

/**
 * Admin analytics data
 */
export interface AdminAnalytics {
  total_revenue: number;
  orders_today: number;
  orders_this_week: number;
  orders_this_month: number;
  active_users: number;
  top_products: { name: string; sales: number; revenue: number }[];
  revenue_by_day: { date: string; amount: number }[];
}

/**
 * Hook for admin products management
 */
export function useAdminProductsTyped() {
  const { get, post, put, del, loading, error } = useApi();
  const [products, setProducts] = useState<AdminProduct[]>([]);

  const getProducts = useCallback(async (): Promise<AdminProduct[]> => {
    try {
      const response = await get('/admin/products');
      const data = response.products || [];
      setProducts(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch admin products:', err);
      return [];
    }
  }, [get]);

  const createProduct = useCallback(async (product: Partial<AdminProduct>): Promise<AdminProduct | null> => {
    try {
      const response = await post('/admin/products', product);
      await getProducts(); // Refresh list
      return response.product;
    } catch (err) {
      console.error('Failed to create product:', err);
      return null;
    }
  }, [post, getProducts]);

  const updateProduct = useCallback(async (id: string, updates: Partial<AdminProduct>): Promise<AdminProduct | null> => {
    try {
      const response = await put(`/admin/products/${id}`, updates);
      await getProducts(); // Refresh list
      return response.product;
    } catch (err) {
      console.error('Failed to update product:', err);
      return null;
    }
  }, [put, getProducts]);

  const deleteProduct = useCallback(async (id: string): Promise<boolean> => {
    try {
      await del(`/admin/products/${id}`);
      await getProducts(); // Refresh list
      return true;
    } catch (err) {
      console.error('Failed to delete product:', err);
      return false;
    }
  }, [del, getProducts]);

  const addStock = useCallback(async (productId: string, credentials: string[], notes?: string): Promise<boolean> => {
    try {
      await post('/admin/stock', { product_id: productId, credentials, notes });
      await getProducts(); // Refresh to update stock count
      return true;
    } catch (err) {
      console.error('Failed to add stock:', err);
      return false;
    }
  }, [post, getProducts]);

  return { products, getProducts, createProduct, updateProduct, deleteProduct, addStock, loading, error };
}

/**
 * Hook for admin orders management
 */
export function useAdminOrdersTyped() {
  const { get, loading, error } = useApi();
  const [orders, setOrders] = useState<AdminOrder[]>([]);

  const getOrders = useCallback(async (status?: string, limit?: number): Promise<AdminOrder[]> => {
    try {
      let url = '/admin/orders';
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (limit) params.append('limit', String(limit));
      if (params.toString()) url += `?${params.toString()}`;
      
      const response = await get(url);
      const data = response.orders || [];
      setOrders(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch admin orders:', err);
      return [];
    }
  }, [get]);

  return { orders, getOrders, loading, error };
}

/**
 * Hook for admin users management
 */
export function useAdminUsersTyped() {
  const { get, put, loading, error } = useApi();
  const [users, setUsers] = useState<AdminUser[]>([]);

  const getUsers = useCallback(async (limit?: number): Promise<AdminUser[]> => {
    try {
      const url = limit ? `/admin/users?limit=${limit}` : '/admin/users';
      const response = await get(url);
      const data = response.users || [];
      setUsers(data);
      return data;
    } catch (err) {
      console.error('Failed to fetch admin users:', err);
      return [];
    }
  }, [get]);

  const updateUserRole = useCallback(async (userId: string, role: string): Promise<boolean> => {
    try {
      await put(`/admin/users/${userId}/role`, { role });
      await getUsers();
      return true;
    } catch (err) {
      console.error('Failed to update user role:', err);
      return false;
    }
  }, [put, getUsers]);

  const banUser = useCallback(async (userId: string, ban: boolean): Promise<boolean> => {
    try {
      await put(`/admin/users/${userId}/ban`, { banned: ban });
      await getUsers();
      return true;
    } catch (err) {
      console.error('Failed to ban/unban user:', err);
      return false;
    }
  }, [put, getUsers]);

  return { users, getUsers, updateUserRole, banUser, loading, error };
}

/**
 * Hook for admin analytics
 */
export function useAdminAnalyticsTyped() {
  const { get, loading, error } = useApi();
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);

  const getAnalytics = useCallback(async (): Promise<AdminAnalytics | null> => {
    try {
      const response = await get('/admin/analytics');
      setAnalytics(response);
      return response;
    } catch (err) {
      console.error('Failed to fetch admin analytics:', err);
      return null;
    }
  }, [get]);

  return { analytics, getAnalytics, loading, error };
}
