/**
 * Admin API Hooks
 * 
 * Type-safe hooks for admin operations.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';

// Types
export interface AdminProduct {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  msrp: number;
  type: 'instant' | 'preorder';
  stock: number;
  fulfillment: number;
  warranty: number;
  duration: number;
  sold: number;
  status: 'active' | 'inactive' | 'discontinued';
  vpn: boolean;
  image?: string;
  video?: string;
  instructions?: string;
  created_at?: string;
}

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

export interface AdminAnalytics {
  total_revenue: number;
  orders_today: number;
  orders_this_week: number;
  orders_this_month: number;
  active_users: number;
  top_products: { name: string; sales: number; revenue: number }[];
  revenue_by_day: { date: string; amount: number }[];
}

// Products Hook
export function useAdminProductsTyped() {
  const { get, post, put, del, loading, error } = useApi();
  const [products, setProducts] = useState<AdminProduct[]>([]);

  const getProducts = useCallback(async (): Promise<AdminProduct[]> => {
    try {
      const response = await get<{ products: AdminProduct[] }>('/admin/products');
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
      const response = await post<{ product: AdminProduct }>('/admin/products', product);
      await getProducts();
      return response.product;
    } catch (err) {
      console.error('Failed to create product:', err);
      return null;
    }
  }, [post, getProducts]);

  const updateProduct = useCallback(async (id: string, updates: Partial<AdminProduct>): Promise<AdminProduct | null> => {
    try {
      const response = await put<{ product: AdminProduct }>(`/admin/products/${id}`, updates);
      await getProducts();
      return response.product;
    } catch (err) {
      console.error('Failed to update product:', err);
      return null;
    }
  }, [put, getProducts]);

  const deleteProduct = useCallback(async (id: string): Promise<boolean> => {
    try {
      await del(`/admin/products/${id}`);
      await getProducts();
      return true;
    } catch (err) {
      console.error('Failed to delete product:', err);
      return false;
    }
  }, [del, getProducts]);

  const addStock = useCallback(async (productId: string, credentials: string[], notes?: string): Promise<boolean> => {
    try {
      await post('/admin/stock', { product_id: productId, credentials, notes });
      await getProducts();
      return true;
    } catch (err) {
      console.error('Failed to add stock:', err);
      return false;
    }
  }, [post, getProducts]);

  return { products, getProducts, createProduct, updateProduct, deleteProduct, addStock, loading, error };
}

// Orders Hook
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
      
      const response = await get<{ orders: AdminOrder[] }>(url);
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

// Users Hook
export function useAdminUsersTyped() {
  const { get, put, loading, error } = useApi();
  const [users, setUsers] = useState<AdminUser[]>([]);

  const getUsers = useCallback(async (limit?: number): Promise<AdminUser[]> => {
    try {
      const url = limit ? `/admin/users?limit=${limit}` : '/admin/users';
      const response = await get<{ users: AdminUser[] }>(url);
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

// Analytics Hook
export function useAdminAnalyticsTyped() {
  const { get, loading, error } = useApi();
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);

  const getAnalytics = useCallback(async (): Promise<AdminAnalytics | null> => {
    try {
      const response = await get<AdminAnalytics>('/admin/analytics');
      setAnalytics(response);
      return response;
    } catch (err) {
      console.error('Failed to fetch admin analytics:', err);
      return null;
    }
  }, [get]);

  return { analytics, getAnalytics, loading, error };
}
