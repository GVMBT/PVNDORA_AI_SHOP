import { useState, useCallback } from 'react';
import { persistSessionTokenFromQuery } from '../utils/auth';
import { apiRequest } from '../utils/apiClient';

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
 * Uses centralized apiRequest for consistent error handling and headers.
 */
export function useApi(): UseApiReturn {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const request = useCallback(async <T = unknown>(endpoint: string, options: RequestOptions = {}): Promise<T> => {
    setLoading(true);
    setError(null);
    
    // Try to capture session_token from URL once (using shared utility)
    persistSessionTokenFromQuery();
    
    try {
      // Use shared apiRequest which handles base URL, headers, and error parsing
      const data = await apiRequest<T>(endpoint, options);
      
      setLoading(false);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setLoading(false);
      throw err;
    }
  }, []);
  
  const get = useCallback(<T = unknown>(endpoint: string) => request<T>(endpoint, { method: 'GET' }), [request]);
  
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

export default useApi;
