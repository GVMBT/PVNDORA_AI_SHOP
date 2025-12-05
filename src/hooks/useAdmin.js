import { useState, useCallback, useEffect } from 'react'

const ADMIN_API_BASE = '/api/admin'

export function useAdmin() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [isAdmin, setIsAdmin] = useState(false)
  const [checking, setChecking] = useState(true)

  const checkAdminStatus = useCallback(async () => {
    if (typeof window === 'undefined') {
      setChecking(false)
      return
    }
    
    try {
      const headers = {
        'Content-Type': 'application/json'
      }
      
      // Try Telegram initData first (Mini App)
      const initData = window.Telegram?.WebApp?.initData || ''
      if (initData) {
        headers['X-Init-Data'] = initData
      } else {
        // Fallback to Bearer token (web session)
        const sessionToken = window.localStorage?.getItem('pvndora_session')
        if (sessionToken) {
          headers['Authorization'] = `Bearer ${sessionToken}`
        }
      }
      
      const response = await fetch('/api/webapp/profile', { headers })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Admin check failed:', response.status, errorText)
        throw new Error(`HTTP ${response.status}`)
      }
      
      const data = await response.json()
      console.log('Admin profile check:', data.profile)
      setIsAdmin(data.profile?.is_admin === true)
    } catch (err) {
      console.error('Failed to check admin status:', err)
      setIsAdmin(false)
    } finally {
      setChecking(false)
    }
  }, [])

  // Check admin status on mount
  useEffect(() => {
    checkAdminStatus()
  }, [checkAdminStatus])

  const getHeaders = useCallback(() => {
    const headers = {
      'Content-Type': 'application/json'
    }
    
    // Try Telegram initData first (Mini App)
    const initData = typeof window !== 'undefined' && window.Telegram?.WebApp?.initData || ''
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

  const adminRequest = useCallback(async (endpoint, options = {}) => {
    setLoading(true)
    setError(null)
    
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${ADMIN_API_BASE}${endpoint}`
      
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

  // Products
  const getProducts = useCallback(() => adminRequest('/products'), [adminRequest])
  const createProduct = useCallback((data) => adminRequest('/products', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest])
  const updateProduct = useCallback((id, data) => adminRequest(`/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }), [adminRequest])

  // Stock
  const getStock = useCallback((productId) => {
    const params = productId ? `?product_id=${productId}` : ''
    return adminRequest(`/stock${params}`)
  }, [adminRequest])
  const addStock = useCallback((data) => adminRequest('/stock', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest])
  const addStockBulk = useCallback((data) => adminRequest('/stock/bulk', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest])

  // Orders
  const getOrders = useCallback((status) => {
    const params = status ? `?status=${status}` : ''
    return adminRequest(`/orders${params}`)
  }, [adminRequest])

  // Tickets
  const getTickets = useCallback((status = 'open') => adminRequest(`/tickets?status=${status}`), [adminRequest])
  const resolveTicket = useCallback((ticketId, approve = true) => 
    adminRequest(`/tickets/${ticketId}/resolve?approve=${approve}`, { method: 'POST' }), [adminRequest])

  // Analytics
  const getAnalytics = useCallback((days = 7) => adminRequest(`/analytics?days=${days}`), [adminRequest])

  // FAQ
  const getFAQ = useCallback(() => adminRequest('/faq'), [adminRequest])
  const createFAQ = useCallback((data) => adminRequest('/faq', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest])

  // Users
  const getUsers = useCallback(() => adminRequest('/users'), [adminRequest])
  const banUser = useCallback((telegramId, ban = true) => 
    adminRequest('/users/ban', {
      method: 'POST',
      body: JSON.stringify({ telegram_id: telegramId, ban })
    }), [adminRequest])

  // Referral System
  const getReferralSettings = useCallback(() => adminRequest('/referral/settings'), [adminRequest])
  const updateReferralSettings = useCallback((data) => adminRequest('/referral/settings', {
    method: 'PUT',
    body: JSON.stringify(data)
  }), [adminRequest])
  const getReferralDashboard = useCallback(() => adminRequest('/referral/dashboard'), [adminRequest])
  const getReferralPartnersCRM = useCallback((sortBy = 'referral_revenue', sortOrder = 'desc', limit = 50, partnerType = 'all') => 
    adminRequest(`/referral/partners-crm?sort_by=${sortBy}&sort_order=${sortOrder}&limit=${limit}&partner_type=${partnerType}`), [adminRequest])
  
  // Users CRM - Extended analytics
  const getUsersCRM = useCallback((sortBy = 'total_orders', sortOrder = 'desc', limit = 50, offset = 0, search = null, filterBanned = null, filterPartner = null) => {
    const params = new URLSearchParams({
      sort_by: sortBy,
      sort_order: sortOrder,
      limit: limit.toString(),
      offset: offset.toString()
    })
    if (search) params.append('search', search)
    if (filterBanned !== null) params.append('filter_banned', filterBanned.toString())
    if (filterPartner !== null) params.append('filter_partner', filterPartner.toString())
    return adminRequest(`/users/crm?${params.toString()}`)
  }, [adminRequest])
  const banUserCRM = useCallback((userId, ban = true) => 
    adminRequest(`/users/${userId}/ban?ban=${ban}`, { method: 'POST' }), [adminRequest])
  const updateUserBalance = useCallback((userId, amount) => 
    adminRequest(`/users/${userId}/balance?amount=${amount}`, { method: 'POST' }), [adminRequest])
  const updateUserWarnings = useCallback((userId, count) => 
    adminRequest(`/users/${userId}/warnings?count=${count}`, { method: 'POST' }), [adminRequest])
  
  const getPartners = useCallback(() => adminRequest('/partners'), [adminRequest])
  const setPartner = useCallback((data) => adminRequest('/partners/set', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest])

  return {
    isAdmin,
    checking,
    loading,
    error,
    adminRequest,
    // Products
    getProducts,
    createProduct,
    updateProduct,
    // Stock
    getStock,
    addStock,
    addStockBulk,
    // Orders
    getOrders,
    // Tickets
    getTickets,
    resolveTicket,
    // Analytics
    getAnalytics,
    // FAQ
    getFAQ,
    createFAQ,
    // Users
    getUsers,
    banUser,
    // Users CRM (Extended Analytics)
    getUsersCRM,
    banUserCRM,
    updateUserBalance,
    updateUserWarnings,
    // Referral
    getReferralSettings,
    updateReferralSettings,
    getReferralDashboard,
    getReferralPartnersCRM,
    getUsersCRM,
    banUserCRM,
    updateUserBalance,
    updateUserWarnings,
    getPartners,
    setPartner,
    // Partner Applications
    getPartnerApplications: useCallback((status = 'pending') => 
      adminRequest(`/partner-applications?status=${status}`), [adminRequest]),
    reviewPartnerApplication: useCallback((data) => 
      adminRequest('/partner-applications/review', {
        method: 'POST',
        body: JSON.stringify(data)
      }), [adminRequest])
  }
}

export default useAdmin

