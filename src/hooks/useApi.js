import { useState, useCallback } from 'react'

const API_BASE = '/api/webapp'

/**
 * Hook for API calls with Telegram initData authentication
 */
export function useApi() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const getHeaders = useCallback(() => {
    const headers = {
      'Content-Type': 'application/json'
    }
    
    // Try Telegram initData first (Mini App)
    const initData = window.Telegram?.WebApp?.initData || ''
    if (initData) {
      headers['X-Init-Data'] = initData
    } else {
      // Fallback to Bearer token (web session)
      const sessionToken = typeof window !== 'undefined' && window.localStorage 
        ? window.localStorage.getItem('pvndora_session')
        : null
      if (sessionToken) {
        headers['Authorization'] = `Bearer ${sessionToken}`
      }
    }
    
    return headers
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
        let errorMessage = errorData.detail || errorData.error || `HTTP ${response.status}`
        
        // Улучшаем сообщения для 429 (Too Many Requests)
        if (response.status === 429) {
          // Убираем технические префиксы из сообщений
          errorMessage = errorMessage.replace(/^1Plat API error:\s*/i, '')
          if (!errorMessage || errorMessage === `HTTP ${response.status}`) {
            errorMessage = 'Слишком много запросов. Подождите минуту и попробуйте снова.'
          }
        }
        
        throw new Error(errorMessage)
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

  const patch = useCallback((endpoint, body) =>
    request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body)
    }), [request])

  const del = useCallback((endpoint) =>
    request(endpoint, {
      method: 'DELETE'
    }), [request])
  
  return {
    loading,
    error,
    get,
    post,
    put,
    patch,
    del,
    request
  }
}

// Specific API hooks
export function useProducts() {
  const { get, loading, error } = useApi()
  
  // Get user language from Telegram or browser
  const getLanguageCode = useCallback(() => {
    const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code
    const browserLang = navigator.language?.split('-')[0]
    return tgLang || browserLang || 'en'
  }, [])
  
  const getProducts = useCallback((category) => {
    const lang = getLanguageCode()
    const params = new URLSearchParams()
    if (category) params.append('category', category)
    params.append('language_code', lang)
    return get(`/products?${params.toString()}`)
  }, [get, getLanguageCode])
  
  const getProduct = useCallback((id) => {
    const lang = getLanguageCode()
    return get(`/products/${id}?language_code=${lang}`)
  }, [get, getLanguageCode])
  
  return { getProducts, getProduct, loading, error }
}

export function useOrders() {
  const { get, post, loading, error } = useApi()
  
  const getOrders = useCallback(() => get('/orders'), [get])
  const getPaymentMethods = useCallback(() => get('/payments/methods'), [get])
  
  const createOrder = useCallback((productId, quantity = 1, promoCode = null, paymentMethod = 'card') => 
    post('/orders', { product_id: productId, quantity, promo_code: promoCode, payment_method: paymentMethod }), 
    [post])
  
  const createOrderFromCart = useCallback((promoCode = null, paymentMethod = 'card') => 
    post('/orders', { use_cart: true, promo_code: promoCode, payment_method: paymentMethod }), 
    [post])
  
  return { getOrders, getPaymentMethods, createOrder, createOrderFromCart, loading, error }
}

export function useCart() {
  const { get, post, patch, del, loading, error } = useApi()
  
  const getCart = useCallback(() => get('/cart'), [get])
  const addToCart = useCallback((productId, quantity = 1) => 
    post('/cart/add', { product_id: productId, quantity }), [post])
  const updateCartItem = useCallback((productId, quantity = 1) => 
    patch('/cart/item', { product_id: productId, quantity }), [patch])
  const removeCartItem = useCallback((productId) => 
    del(`/cart/item?product_id=${encodeURIComponent(productId)}`), [del])
  const applyCartPromo = useCallback((code) => 
    post('/cart/promo/apply', { code }), [post])
  const removeCartPromo = useCallback(() => post('/cart/promo/remove', {}), [post])
  
  return { getCart, addToCart, updateCartItem, removeCartItem, applyCartPromo, removeCartPromo, loading, error }
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


