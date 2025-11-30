import { useState, useCallback } from 'react'

const API_BASE = '/api/webapp'

/**
 * Hook for API calls with Telegram initData authentication
 */
export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const getHeaders = useCallback(() => {
    const initData = window.Telegram?.WebApp?.initData || ''
    return {
      'Content-Type': 'application/json',
      'X-Init-Data': initData
    }
  }, [])
  
  const request = useCallback(async (endpoint, options = {}) => {
    setLoading(true)
    setError(null)
    
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`
      
      const response = await fetch(url, {
        ...options,
        headers: {
          ...getHeaders(),
          ...options.headers
        }
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}`)
      }
      
      const data = await response.json()
      setLoading(false)
      return data
    } catch (err) {
      setError(err.message)
      setLoading(false)
      throw err
    }
  }, [getHeaders])
  
  const get = useCallback((endpoint) => request(endpoint), [request])
  
  const post = useCallback((endpoint, body) => 
    request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    }), [request])
  
  const put = useCallback((endpoint, body) =>
    request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    }), [request])
  
  return {
    loading,
    error,
    get,
    post,
    put,
    request
  }
}

// Specific API hooks
export function useProducts() {
  const { get, loading, error } = useApi()
  
  const getProducts = useCallback((category) => {
    const params = category ? `?category=${category}` : ''
    return get(`/products${params}`)
  }, [get])
  
  const getProduct = useCallback((id) => get(`/products/${id}`), [get])
  
  return { getProducts, getProduct, loading, error }
}

export function useOrders() {
  const { get, post, loading, error } = useApi()
  
  const getOrders = useCallback(() => get('/orders'), [get])
  
  const createOrder = useCallback((productId, quantity = 1, promoCode = null) => 
    post('/orders', { product_id: productId, quantity, promo_code: promoCode }), 
    [post])
  
  const createOrderFromCart = useCallback((promoCode = null) => 
    post('/orders', { use_cart: true, promo_code: promoCode }), 
    [post])
  
  return { getOrders, createOrder, createOrderFromCart, loading, error }
}

export function useCart() {
  const { get, loading, error } = useApi()
  
  const getCart = useCallback(() => get('/cart'), [get])
  
  return { getCart, loading, error }
}

export function useLeaderboard() {
  const { get, loading, error } = useApi()
  
  const getLeaderboard = useCallback(() => get('/leaderboard'), [get])
  
  return { getLeaderboard, loading, error }
}

export function useFAQ() {
  const { get, loading, error } = useApi()
  
  const getFAQ = useCallback((lang = 'en') => get(`/faq?language_code=${lang}`), [get])
  
  return { getFAQ, loading, error }
}

export function usePromo() {
  const { post, loading, error } = useApi()
  
  const checkPromo = useCallback((code) => post('/promo/check', { code }), [post])
  
  return { checkPromo, loading, error }
}

export function useReviews() {
  const { post, loading, error } = useApi()
  
  const submitReview = useCallback((orderId, rating, text = null) => 
    post('/reviews', { order_id: orderId, rating, text }), 
    [post])
  
  return { submitReview, loading, error }
}

export default useApi


