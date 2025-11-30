import { useState, useCallback, useEffect } from 'react'
import { useApi } from './useApi'

const ADMIN_API_BASE = '/api/admin'

export function useAdmin() {
  const { get, post, put, loading, error, request } = useApi()
  const [isAdmin, setIsAdmin] = useState(false)
  const [checking, setChecking] = useState(true)

  // Check admin status on mount
  useEffect(() => {
    checkAdminStatus()
  }, [])

  const checkAdminStatus = useCallback(async () => {
    try {
      // Use full path to bypass /api/webapp prefix
      const initData = window.Telegram?.WebApp?.initData || ''
      const response = await fetch('/api/user/profile', {
        headers: {
          'Content-Type': 'application/json',
          'X-Init-Data': initData
        }
      })
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Admin check failed:', response.status, errorText)
        throw new Error(`HTTP ${response.status}`)
      }
      
      const profile = await response.json()
      console.log('Admin profile check:', profile)
      setIsAdmin(profile.is_admin === true)
    } catch (err) {
      console.error('Failed to check admin status:', err)
      setIsAdmin(false)
    } finally {
      setChecking(false)
    }
  }, [])

  // Products
  const getProducts = useCallback(() => get(`${ADMIN_API_BASE}/products`), [get])
  const createProduct = useCallback((data) => post(`${ADMIN_API_BASE}/products`, data), [post])
  const updateProduct = useCallback((id, data) => put(`${ADMIN_API_BASE}/products/${id}`, data), [put])

  // Stock
  const getStock = useCallback((productId) => {
    const params = productId ? `?product_id=${productId}` : ''
    return get(`${ADMIN_API_BASE}/stock${params}`)
  }, [get])
  const addStock = useCallback((data) => post(`${ADMIN_API_BASE}/stock`, data), [post])
  const addStockBulk = useCallback((data) => post(`${ADMIN_API_BASE}/stock/bulk`, data), [post])

  // Orders
  const getOrders = useCallback((status) => {
    const params = status ? `?status=${status}` : ''
    return get(`${ADMIN_API_BASE}/orders${params}`)
  }, [get])

  // Tickets
  const getTickets = useCallback((status = 'open') => get(`${ADMIN_API_BASE}/tickets?status=${status}`), [get])
  const resolveTicket = useCallback((ticketId, approve = true) => 
    post(`${ADMIN_API_BASE}/tickets/${ticketId}/resolve?approve=${approve}`), [post])

  // Analytics
  const getAnalytics = useCallback((days = 7) => get(`${ADMIN_API_BASE}/analytics?days=${days}`), [get])

  // FAQ
  const getFAQ = useCallback(() => get(`${ADMIN_API_BASE}/faq`), [get])
  const createFAQ = useCallback((data) => post(`${ADMIN_API_BASE}/faq`, data), [post])

  // Users
  const getUsers = useCallback(() => get(`${ADMIN_API_BASE}/users`), [get])
  const banUser = useCallback((telegramId, ban = true) => 
    post(`${ADMIN_API_BASE}/users/ban`, { telegram_id: telegramId, ban }), [post])

  return {
    isAdmin,
    checking,
    loading,
    error,
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
    banUser
  }
}

export default useAdmin

