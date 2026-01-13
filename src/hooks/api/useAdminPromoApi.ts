/**
 * Admin Promo Codes API Hook
 *
 * Hook for managing promo codes in admin panel.
 * Uses /api/admin base URL (not /api/webapp).
 */

import { useState, useCallback } from "react";
import { apiRequest } from "../../utils/apiClient";
import { API } from "../../config";
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

export interface PromoCodeData {
  id: string;
  code: string;
  discount_percent: number;
  expires_at?: string | null;
  usage_limit?: number | null;
  usage_count: number;
  is_active: boolean;
  product_id?: string | null; // NULL = cart-wide, NOT NULL = product-specific
  created_at: string;
}

export function useAdminPromoTyped() {
  const [promoCodes, setPromoCodes] = useState<PromoCodeData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getPromoCodes = useCallback(async (): Promise<PromoCodeData[]> => {
    setLoading(true);
    try {
      const data = await adminRequest<PromoCodeData[]>("/promo");
      setPromoCodes(data || []);
      return data || [];
    } catch (err) {
      logger.error("Failed to fetch promo codes", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const createPromoCode = useCallback(
    async (
      data: Omit<PromoCodeData, "id" | "usage_count" | "created_at">
    ): Promise<PromoCodeData | null> => {
      try {
        const result = await adminRequest<PromoCodeData>("/promo", {
          method: "POST",
          body: JSON.stringify(data),
        });
        if (result) {
          setPromoCodes((prev) => [result, ...prev]);
        }
        return result;
      } catch (err) {
        logger.error("Failed to create promo code", err);
        throw err;
      }
    },
    []
  );

  const updatePromoCode = useCallback(
    async (id: string, data: Partial<PromoCodeData>): Promise<PromoCodeData | null> => {
      try {
        const result = await adminRequest<PromoCodeData>(`/promo/${id}`, {
          method: "PUT",
          body: JSON.stringify(data),
        });
        if (result) {
          setPromoCodes((prev) => prev.map((p) => (p.id === id ? result : p)));
        }
        return result;
      } catch (err) {
        logger.error("Failed to update promo code", err);
        throw err;
      }
    },
    []
  );

  const deletePromoCode = useCallback(async (id: string): Promise<void> => {
    try {
      await adminRequest(`/promo/${id}`, { method: "DELETE" });
      setPromoCodes((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      logger.error("Failed to delete promo code", err);
      throw err;
    }
  }, []);

  const togglePromoActive = useCallback(async (id: string, isActive: boolean): Promise<void> => {
    try {
      const result = await adminRequest<PromoCodeData>(`/promo/${id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: isActive }),
      });
      if (result) {
        setPromoCodes((prev) => prev.map((p) => (p.id === id ? result : p)));
      }
    } catch (err) {
      logger.error("Failed to toggle promo code", err);
      throw err;
    }
  }, []);

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
