import { useState, useCallback } from 'react';
import { API } from '../config';
import { persistSessionTokenFromQuery } from '../utils/auth';
import { getApiHeaders, type ApiHeaders } from '../utils/apiHeaders';
import { logger } from '../utils/logger';

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

interface UseApiReturn {
  loading: boolean;
  error: string | null;
  get: <T = unknown>(endpoint: string) => Promise<T>;
  post: <T = unknown>(endpoint: string, body: unknown) => Promise<T>;
  put: <T = unknown>(endpoint: string, body: unknown) => Promise<T>;
  patch: <T = unknown>(endpoint: string, body: unknown) => Promise<T>;
  del: <T = unknown>(endpoint: string) => Promise<T>;
  request: <T = unknown>(endpoint: string, options?: RequestOptions) => Promise<T>;
}

/**
 * Hook for API calls with Telegram initData authentication
 */
export function useApi(): UseApiReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const getHeaders = useCallback((): ApiHeaders => {
    // Try to capture session_token from URL once (using shared utility)
    persistSessionTokenFromQuery();
    // Use centralized header generation
    return getApiHeaders();
  }, []);
  
  const request = useCallback(async <T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> => {
    setLoading(true);
    setError(null);
    
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${API.BASE_URL}${endpoint}`;
      
      const response = await fetch(url, {
        ...options,
        headers: {
          ...getHeaders(),
          ...options.headers
        }
      });
      
      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}`;
        
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorData.message || errorMessage;
        } catch {
          try {
            const textError = await response.text();
            if (textError && textError.length < 200) {
              errorMessage = textError;
            }
          } catch {
            // Ignore
          }
        }
        
        if (response.status === 429) {
          errorMessage = errorMessage.replace(/^(1Plat|Rukassa) API error:\s*/i, '');
          if (!errorMessage || errorMessage === `HTTP ${response.status}`) {
            errorMessage = 'Слишком много запросов. Подождите минуту и попробуйте снова.';
          }
        } else if (response.status === 502 || response.status === 503) {
          errorMessage = 'Платёжная система временно недоступна. Попробуйте позже.';
        }
        
        throw new Error(errorMessage);
      }
      
      let data: T;
      try {
        data = await response.json();
      } catch {
        logger.warn('API returned non-JSON response', { endpoint });
        data = {} as T;
      }
      setLoading(false);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setLoading(false);
      throw err;
    }
  }, [getHeaders]);
  
  const get = useCallback(<T = unknown>(endpoint: string) => request<T>(endpoint), [request]);
  
  const post = useCallback(<T = unknown>(endpoint: string, body: unknown) => 
    request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    }), [request]);
  
  const put = useCallback(<T = unknown>(endpoint: string, body: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    }), [request]);

  const patch = useCallback(<T = unknown>(endpoint: string, body: unknown) =>
    request<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body)
    }), [request]);

  const del = useCallback(<T = unknown>(endpoint: string) =>
    request<T>(endpoint, {
      method: 'DELETE'
    }), [request]);
  
  return {
    loading,
    error,
    get,
    post,
    put,
    patch,
    del,
    request
  };
}

/**
 * Base API hook - used by typed API hooks in hooks/api/
 * 
 * For domain-specific typed hooks, use hooks from useApiTyped.ts:
 * - useProductsTyped
 * - useOrdersTyped
 * - useProfileTyped
 * - useLeaderboardTyped
 * - useReviewsTyped, useSupportTyped, useAIChatTyped, usePromoTyped
 */

export default useApi;
