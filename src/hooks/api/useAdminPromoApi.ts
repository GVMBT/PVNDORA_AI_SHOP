/**
 * Admin Promo Codes API Hook
 * 
 * Hook for managing promo codes in admin panel.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';
import { logger } from '../../utils/logger';

export interface PromoCodeData {
  id: string;
  code: string;
  discount_percent: number;
  expires_at?: string | null;
  usage_limit?: number | null;
  usage_count: number;
  is_active: boolean;
  created_at: string;
}

export function useAdminPromoTyped() {
  const { get, post, put, del, loading, error } = useApi();
  const [promoCodes, setPromoCodes] = useState<PromoCodeData[]>([]);

  const getPromoCodes = useCallback(async (): Promise<PromoCodeData[]> => {
    try {
      const data = await get<PromoCodeData[]>('/admin/promo');
      setPromoCodes(data || []);
      return data || [];
    } catch (err) {
      logger.error('Failed to fetch promo codes', err);
      return [];
    }
  }, [get]);

  const createPromoCode = useCallback(async (
    data: Omit<PromoCodeData, 'id' | 'usage_count' | 'created_at'>
  ): Promise<PromoCodeData | null> => {
    try {
      const result = await post<PromoCodeData>('/admin/promo', data);
      if (result) {
        setPromoCodes(prev => [result, ...prev]);
      }
      return result;
    } catch (err) {
      logger.error('Failed to create promo code', err);
      throw err;
    }
  }, [post]);

  const updatePromoCode = useCallback(async (
    id: string,
    data: Partial<PromoCodeData>
  ): Promise<PromoCodeData | null> => {
    try {
      const result = await put<PromoCodeData>(`/admin/promo/${id}`, data);
      if (result) {
        setPromoCodes(prev => prev.map(p => p.id === id ? result : p));
      }
      return result;
    } catch (err) {
      logger.error('Failed to update promo code', err);
      throw err;
    }
  }, [put]);

  const deletePromoCode = useCallback(async (id: string): Promise<void> => {
    try {
      await del(`/admin/promo/${id}`);
      setPromoCodes(prev => prev.filter(p => p.id !== id));
    } catch (err) {
      logger.error('Failed to delete promo code', err);
      throw err;
    }
  }, [del]);

  const togglePromoActive = useCallback(async (id: string, isActive: boolean): Promise<void> => {
    try {
      const result = await put<PromoCodeData>(`/admin/promo/${id}`, { is_active: isActive });
      if (result) {
        setPromoCodes(prev => prev.map(p => p.id === id ? result : p));
      }
    } catch (err) {
      logger.error('Failed to toggle promo code', err);
      throw err;
    }
  }, [put]);

  return {
    promoCodes,
    getPromoCodes,
    createPromoCode,
    updatePromoCode,
    deletePromoCode,
    togglePromoActive,
    loading,
    error,
  };
}
