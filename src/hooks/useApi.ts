import { useState, useCallback } from 'react';
import { API, CACHE } from '../config';

interface ApiHeaders {
  'Content-Type': string;
  'X-Init-Data'?: string;
  Authorization?: string;
}

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
    // Try to capture session_token from URL once
    if (typeof window !== 'undefined') {
      try {
        const url = new URL(window.location.href);
        const token = url.searchParams.get('session_token');
        if (token) {
          window.localStorage?.setItem(CACHE.SESSION_TOKEN_KEY, token);
          url.searchParams.delete('session_token');
          window.history.replaceState({}, '', url.toString());
        }
      } catch {
        /* ignore */
      }
    }

    const headers: ApiHeaders = {
      'Content-Type': 'application/json'
    };
    
    // Try Telegram initData first (Mini App)
    const initData = (window as any).Telegram?.WebApp?.initData || '';
    if (initData) {
      headers['X-Init-Data'] = initData;
    } else {
      // Fallback to Bearer token (web session)
      const sessionToken = typeof window !== 'undefined' && window.localStorage 
        ? window.localStorage.getItem(CACHE.SESSION_TOKEN_KEY)
        : null;
      if (sessionToken) {
        headers['Authorization'] = `Bearer ${sessionToken}`;
      }
    }
    
    return headers;
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
        console.warn('API returned non-JSON response');
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

// Specific API hooks with types

interface ProductsResponse {
  products: unknown[];
  currency?: string;
}

interface ProductResponse {
  product: unknown;
}

export function useProducts() {
  const { get, loading, error } = useApi();
  
  const getLanguageCode = useCallback((): string => {
    const tgLang = (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
    const browserLang = navigator.language?.split('-')[0];
    return tgLang || browserLang || 'en';
  }, []);
  
  const getProducts = useCallback((category?: string) => {
    const lang = getLanguageCode();
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    params.append('language_code', lang);
    return get<ProductsResponse>(`/products?${params.toString()}`);
  }, [get, getLanguageCode]);
  
  const getProduct = useCallback((id: string) => {
    const lang = getLanguageCode();
    return get<ProductResponse>(`/products/${id}?language_code=${lang}`);
  }, [get, getLanguageCode]);
  
  return { getProducts, getProduct, loading, error };
}

interface OrdersResponse {
  orders: unknown[];
}

interface PaymentMethodsResponse {
  systems: Array<{
    system_group: string;
    name: string;
    icon?: string;
  }>;
}

interface OrderResponse {
  order_id: string;
  payment_url?: string;
}

export function useOrders() {
  const { get, post, loading, error } = useApi();
  
  const getOrders = useCallback(({ limit, offset }: { limit?: number; offset?: number } = {}) => {
    const params = new URLSearchParams();
    if (limit) params.append('limit', String(limit));
    if (offset) params.append('offset', String(offset));
    const qs = params.toString();
    return get<OrdersResponse>(`/orders${qs ? `?${qs}` : ''}`);
  }, [get]);
  
  const getPaymentMethods = useCallback((gateway?: string) => 
    get<PaymentMethodsResponse>(`/payments/methods${gateway ? `?gateway=${gateway}` : ''}`), [get]);
  
  const createOrder = useCallback((
    productId: string, 
    quantity = 1, 
    promoCode: string | null = null, 
    paymentMethod = 'card', 
    paymentGateway: string | null = null
  ) => 
    post<OrderResponse>('/orders', { 
      product_id: productId, 
      quantity, 
      promo_code: promoCode, 
      payment_method: paymentMethod, 
      payment_gateway: paymentGateway 
    }), 
    [post]);
  
  const createOrderFromCart = useCallback((
    promoCode: string | null = null, 
    paymentMethod = 'card', 
    paymentGateway: string | null = null
  ) => 
    post<OrderResponse>('/orders', { 
      use_cart: true, 
      promo_code: promoCode, 
      payment_method: paymentMethod, 
      payment_gateway: paymentGateway 
    }), 
    [post]);
  
  return { getOrders, getPaymentMethods, createOrder, createOrderFromCart, loading, error };
}

interface CartResponse {
  items: unknown[];
  total?: number;
  subtotal?: number;
  promo_code?: string;
  promo_discount_percent?: number;
  currency?: string;
}

export function useCartApi() {
  const { get, post, patch, del, loading, error } = useApi();
  
  const getCart = useCallback(() => get<CartResponse>('/cart'), [get]);
  const addToCart = useCallback((productId: string, quantity = 1) => 
    post<CartResponse>('/cart/add', { product_id: productId, quantity }), [post]);
  const updateCartItem = useCallback((productId: string, quantity = 1) => 
    patch<CartResponse>('/cart/item', { product_id: productId, quantity }), [patch]);
  const removeCartItem = useCallback((productId: string) => 
    del<CartResponse>(`/cart/item?product_id=${encodeURIComponent(productId)}`), [del]);
  const applyCartPromo = useCallback((code: string) => 
    post<CartResponse>('/cart/promo/apply', { code }), [post]);
  const removeCartPromo = useCallback(() => post<CartResponse>('/cart/promo/remove', {}), [post]);
  
  return { getCart, addToCart, updateCartItem, removeCartItem, applyCartPromo, removeCartPromo, loading, error };
}

interface LeaderboardResponse {
  users: unknown[];
}

export function useLeaderboard() {
  const { get, loading, error } = useApi();
  
  const getLeaderboard = useCallback(() => get<LeaderboardResponse>('/leaderboard'), [get]);
  
  return { getLeaderboard, loading, error };
}

interface FAQResponse {
  faq: unknown[];
}

export function useFAQ() {
  const { get, loading, error } = useApi();
  
  const getFAQ = useCallback((lang = 'en') => get<FAQResponse>(`/faq?language_code=${lang}`), [get]);
  
  return { getFAQ, loading, error };
}

interface PromoResult {
  is_valid: boolean;
  discount_percent?: number;
  discount_amount?: number;
  error?: string;
}

export function usePromo() {
  const { post, loading, error } = useApi();
  
  const checkPromo = useCallback((code: string) => post<PromoResult>('/promo/check', { code }), [post]);
  
  return { checkPromo, loading, error };
}

interface ReviewResponse {
  success: boolean;
}

export function useReviews() {
  const { post, loading, error } = useApi();
  
  const submitReview = useCallback((orderId: string, rating: number, text: string | null = null) => 
    post<ReviewResponse>('/reviews', { order_id: orderId, rating, text }), 
    [post]);
  
  return { submitReview, loading, error };
}

export default useApi;
