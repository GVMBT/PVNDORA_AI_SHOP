/**
 * Admin API Hooks
 *
 * Type-safe hooks for admin operations.
 * Uses /api/admin base URL (not /api/webapp).
 */

import { useCallback, useState } from "react";
import { API } from "../../config";
import { apiRequest } from "../../utils/apiClient";
import { logger } from "../../utils/logger";

/**
 * Admin API request helper - uses /api/admin prefix
 */
async function adminRequest<T>(
  endpoint: string,
  options: { method?: string; body?: string } = {}
): Promise<T> {
  const url = `${API.ADMIN_URL}${endpoint}`;
  return apiRequest<T>(url, options);
}

// Types
export interface AdminProduct {
  id: string;
  name: string;
  description: string;

  // Category (maps to `type` in DB)
  category: string; // ai, dev, design, music

  // Pricing
  price: number;
  prices?: Record<string, number>; // Anchor prices: {RUB: 990, USD: 10.50}
  msrp: number;
  // msrp_prices removed - use msrp (always in RUB)
  discountPrice?: number; // Price for discount channel
  costPrice?: number; // Cost for accounting

  // Fulfillment
  fulfillmentType?: string; // 'auto' or 'manual'
  fulfillment: number; // fulfillment_time_hours

  // Product Settings
  warranty: number; // warranty_hours
  duration: number; // duration_days
  status: "active" | "inactive" | "discontinued";

  // Stock (read-only, calculated)
  stock: number;
  sold: number;

  // Media
  image?: string;
  video?: string;

  // Content
  instructions?: string;

  // Timestamps
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
  balance_currency?: string;
  total_spent: number;
  orders_count: number;
  is_banned: boolean;
  created_at: string;
  // Partner fields
  total_referral_earnings?: number;
  partner_mode?: "commission" | "discount";
}

export interface AdminAnalytics {
  total_revenue: number;
  orders_today: number;
  orders_this_week: number;
  orders_this_month: number;
  active_users: number;
  open_tickets?: number;
  top_products: { name: string; sales: number; revenue: number }[];
  revenue_by_day: { date: string; amount: number }[];
}

export interface StockItem {
  id: string;
  product_id: string;
  content: string;
  status: "available" | "reserved" | "sold";
  created_at?: string;
  reserved_at?: string;
  sold_at?: string;
}

// Products Hook
export function useAdminProductsTyped() {
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getProducts = useCallback(async (): Promise<AdminProduct[]> => {
    setLoading(true);
    try {
      const response = await adminRequest<{ products: AdminProduct[] }>("/products");
      const data = response.products || [];
      setProducts(data);
      return data;
    } catch (err) {
      logger.error("Failed to fetch admin products", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const createProduct = useCallback(
    async (product: Partial<AdminProduct>): Promise<AdminProduct | null> => {
      try {
        const response = await adminRequest<{ product: AdminProduct }>("/products", {
          method: "POST",
          body: JSON.stringify(product),
        });
        await getProducts();
        return response.product;
      } catch (err) {
        logger.error("Failed to create product:", err);
        return null;
      }
    },
    [getProducts]
  );

  const updateProduct = useCallback(
    async (id: string, updates: Partial<AdminProduct>): Promise<AdminProduct | null> => {
      try {
        const response = await adminRequest<{ product: AdminProduct }>(`/products/${id}`, {
          method: "PUT",
          body: JSON.stringify(updates),
        });
        await getProducts();
        return response.product;
      } catch (err) {
        logger.error("Failed to update product", err);
        return null;
      }
    },
    [getProducts]
  );

  const deleteProduct = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        await adminRequest(`/products/${id}`, { method: "DELETE" });
        await getProducts();
        return true;
      } catch (err) {
        logger.error("Failed to delete product", err);
        return false;
      }
    },
    [getProducts]
  );

  const addStockBulk = useCallback(
    async (productId: string, items: string[]): Promise<boolean> => {
      try {
        const response = await adminRequest<{ success: boolean; added_count: number }>(
          "/stock/bulk",
          {
            method: "POST",
            body: JSON.stringify({ product_id: productId, items }),
          }
        );
        await getProducts();
        return response.success;
      } catch (err) {
        logger.error("Failed to add stock", err);
        return false;
      }
    },
    [getProducts]
  );

  const deleteStockItem = useCallback(
    async (stockItemId: string): Promise<boolean> => {
      try {
        await adminRequest(`/stock/${stockItemId}`, { method: "DELETE" });
        await getProducts();
        return true;
      } catch (err) {
        logger.error("Failed to delete stock item", err);
        return false;
      }
    },
    [getProducts]
  );

  const getStock = useCallback(
    async (productId?: string, availableOnly = true): Promise<StockItem[]> => {
      try {
        let url = "/stock";
        const params = new URLSearchParams();
        if (productId) params.append("product_id", productId);
        if (!availableOnly) params.append("available_only", "false");
        if (params.toString()) url += `?${params.toString()}`;

        const response = await adminRequest<{ stock: StockItem[] }>(url);
        return response.stock || [];
      } catch (err) {
        logger.error("Failed to fetch stock", err);
        return [];
      }
    },
    []
  );

  return {
    products,
    getProducts,
    createProduct,
    updateProduct,
    deleteProduct,
    addStockBulk,
    deleteStockItem,
    getStock,
    loading,
    error,
  };
}

// Orders Hook
export function useAdminOrdersTyped() {
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getOrders = useCallback(async (status?: string, limit?: number): Promise<AdminOrder[]> => {
    setLoading(true);
    try {
      let url = "/orders";
      const params = new URLSearchParams();
      if (status) params.append("status", status);
      if (limit) params.append("limit", String(limit));
      if (params.toString()) url += `?${params.toString()}`;

      const response = await adminRequest<{ orders: AdminOrder[] }>(url);
      const data = response.orders || [];
      setOrders(data);
      return data;
    } catch (err) {
      logger.error("Failed to fetch admin orders", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  return { orders, getOrders, loading, error };
}

// Users Hook
export function useAdminUsersTyped() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getUsers = useCallback(async (limit?: number): Promise<AdminUser[]> => {
    setLoading(true);
    try {
      const url = limit ? `/users?limit=${limit}` : "/users";
      const response = await adminRequest<{ users: AdminUser[] }>(url);
      const data = response.users || [];
      setUsers(data);
      return data;
    } catch (err) {
      logger.error("Failed to fetch admin users", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const updateUserRole = useCallback(
    async (userId: string, role: string): Promise<boolean> => {
      try {
        await adminRequest(`/users/${userId}/role`, {
          method: "POST",
          body: JSON.stringify({ role }),
        });
        await getUsers();
        return true;
      } catch (err) {
        logger.error("Failed to update user role", err);
        return false;
      }
    },
    [getUsers]
  );

  const banUser = useCallback(
    async (userId: string, ban: boolean): Promise<boolean> => {
      try {
        await adminRequest(`/users/${userId}/ban?ban=${ban}`, {
          method: "POST",
        });
        await getUsers();
        return true;
      } catch (err) {
        logger.error("Failed to ban/unban user", err);
        return false;
      }
    },
    [getUsers]
  );

  const updateBalance = useCallback(
    async (userId: string, amount: number): Promise<boolean> => {
      try {
        await adminRequest(`/users/${userId}/balance`, {
          method: "POST",
          body: JSON.stringify({ amount }),
        });
        await getUsers();
        return true;
      } catch (err) {
        logger.error("Failed to update balance", err);
        return false;
      }
    },
    [getUsers]
  );

  return { users, getUsers, updateUserRole, banUser, updateBalance, loading, error };
}

// Analytics Hook
export function useAdminAnalyticsTyped() {
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getAnalytics = useCallback(async (): Promise<AdminAnalytics | null> => {
    setLoading(true);
    try {
      const response = await adminRequest<AdminAnalytics>("/analytics");
      setAnalytics(response);
      return response;
    } catch (err) {
      logger.error("Failed to fetch admin analytics", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { analytics, getAnalytics, loading, error };
}
