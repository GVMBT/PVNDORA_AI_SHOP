/**
 * Admin Migration API Hook
 * 
 * Hook for fetching migration statistics in admin panel.
 */

import { useState, useCallback } from 'react';
import { apiRequest } from '../../utils/apiClient';
import { API } from '../../config';
import { logger } from '../../utils/logger';

/**
 * Admin API request helper - uses /api/admin prefix
 */
async function adminRequest<T>(endpoint: string, options: { method?: string; body?: string } = {}): Promise<T> {
  const url = `${API.ADMIN_URL}${endpoint}`;
  return apiRequest<T>(url, options);
}

export interface MigrationStats {
  total_discount_users: number;
  total_pvndora_users: number;
  migrated_users: number;
  migration_rate: number;
  discount_orders: number;
  pvndora_orders_from_discount: number;
  discount_revenue: number;
  pvndora_revenue_from_migrated: number;
  promos_generated: number;
  promos_used: number;
  promo_conversion_rate: number;
}

export interface MigrationTrend {
  date: string;
  new_discount_users?: number;
  migrated_users?: number;
  discount_orders: number;
  pvndora_orders: number;
}

export interface TopMigratingProduct {
  product_id: string;
  name: string;
  category: string;
  migration_orders: number;
}

export function useAdminMigrationApi() {
  const [stats, setStats] = useState<MigrationStats | null>(null);
  const [trend, setTrend] = useState<MigrationTrend[]>([]);
  const [topProducts, setTopProducts] = useState<TopMigratingProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getStats = useCallback(async (days: number = 30): Promise<MigrationStats | null> => {
    setLoading(true);
    try {
      const data = await adminRequest<MigrationStats>(`/migration/stats?days=${days}`);
      setStats(data);
      return data;
    } catch (err) {
      logger.error('Failed to fetch migration stats', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const getTrend = useCallback(async (days: number = 14): Promise<MigrationTrend[]> => {
    setLoading(true);
    try {
      const data = await adminRequest<MigrationTrend[]>(`/migration/trend?days=${days}`);
      setTrend(data || []);
      return data || [];
    } catch (err) {
      logger.error('Failed to fetch migration trend', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const getTopProducts = useCallback(async (limit: number = 10): Promise<TopMigratingProduct[]> => {
    setLoading(true);
    try {
      const data = await adminRequest<TopMigratingProduct[]>(`/migration/top-products?limit=${limit}`);
      setTopProducts(data || []);
      return data || [];
    } catch (err) {
      logger.error('Failed to fetch top migrating products', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    stats,
    trend,
    topProducts,
    loading,
    error,
    getStats,
    getTrend,
    getTopProducts,
  };
}
