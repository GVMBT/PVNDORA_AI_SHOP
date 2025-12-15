import { useState, useCallback, useEffect } from 'react';
import { API } from '../config';
import { logger } from '../utils/logger';
import { apiGet, apiRequest, apiPost, apiPut } from '../utils/apiClient';

export function useAdmin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [checking, setChecking] = useState(true);

  const checkAdminStatus = useCallback(async () => {
    if (typeof window === 'undefined') {
      setChecking(false);
      return;
    }
    
    try {
      // Use apiClient for consistent error handling
      const data = await apiGet<{ profile: { is_admin?: boolean } }>('/profile');
      logger.debug('Admin profile check', data.profile);
      setIsAdmin(data.profile?.is_admin === true);
    } catch (err) {
      logger.error('Failed to check admin status', err);
      setIsAdmin(false);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    checkAdminStatus();
  }, [checkAdminStatus]);

  /**
   * Admin request wrapper using apiClient for consistent error handling
   */
  const adminRequest = useCallback(async <T = unknown>(
    endpoint: string, 
    options: { method?: string; body?: string } = {}
  ): Promise<T> => {
    setLoading(true);
    setError(null);
    
    try {
      // Build full admin URL
      const url = endpoint.startsWith('http') ? endpoint : `${API.ADMIN_URL}${endpoint}`;
      
      // Use apiRequest from apiClient for consistent error handling
      const data = await apiRequest<T>(url, {
        method: options.method || 'GET',
        body: options.body,
      });
      
      setLoading(false);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      setLoading(false);
      throw err;
    }
  }, []);

  // Products
  const getProducts = useCallback(() => adminRequest('/products'), [adminRequest]);
  const createProduct = useCallback((data: unknown) => adminRequest('/products', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest]);
  const updateProduct = useCallback((id: string, data: unknown) => adminRequest(`/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  }), [adminRequest]);

  // Stock
  const getStock = useCallback((productId?: string) => {
    const params = productId ? `?product_id=${productId}` : '';
    return adminRequest(`/stock${params}`);
  }, [adminRequest]);
  const addStock = useCallback((data: unknown) => adminRequest('/stock', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest]);
  const addStockBulk = useCallback((data: unknown) => adminRequest('/stock/bulk', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest]);

  // Orders
  const getOrders = useCallback((status?: string) => {
    const params = status ? `?status=${status}` : '';
    return adminRequest(`/orders${params}`);
  }, [adminRequest]);

  // Tickets
  const getTickets = useCallback((status = 'open') => adminRequest(`/tickets?status=${status}`), [adminRequest]);
  const resolveTicket = useCallback((ticketId: string, approve = true, comment?: string) => {
    const params = new URLSearchParams({ approve: approve.toString() });
    if (comment) {
      params.append('comment', comment);
    }
    return adminRequest(`/tickets/${ticketId}/resolve?${params.toString()}`, { method: 'POST' });
  }, [adminRequest]);

  // Analytics
  const getAnalytics = useCallback((days = 7) => adminRequest(`/analytics?days=${days}`), [adminRequest]);

  // FAQ
  const getFAQ = useCallback(() => adminRequest('/faq'), [adminRequest]);
  const createFAQ = useCallback((data: unknown) => adminRequest('/faq', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest]);

  // Users
  const getUsers = useCallback(() => adminRequest('/users'), [adminRequest]);
  const banUser = useCallback((telegramId: number, ban = true) => 
    adminRequest('/users/ban', {
      method: 'POST',
      body: JSON.stringify({ telegram_id: telegramId, ban })
    }), [adminRequest]);

  // Referral System
  const getReferralSettings = useCallback(() => adminRequest('/referral/settings'), [adminRequest]);
  const updateReferralSettings = useCallback((data: unknown) => adminRequest('/referral/settings', {
    method: 'PUT',
    body: JSON.stringify(data)
  }), [adminRequest]);
  const getReferralDashboard = useCallback(() => adminRequest('/referral/dashboard'), [adminRequest]);
  const getReferralPartnersCRM = useCallback((
    sortBy = 'referral_revenue', 
    sortOrder = 'desc', 
    limit = 50, 
    partnerType = 'all'
  ) => 
    adminRequest(`/referral/partners-crm?sort_by=${sortBy}&sort_order=${sortOrder}&limit=${limit}&partner_type=${partnerType}`), [adminRequest]);
  
  // Users CRM
  const getUsersCRM = useCallback((
    sortBy = 'total_orders', 
    sortOrder = 'desc', 
    limit = 50, 
    offset = 0, 
    search: string | null = null, 
    filterBanned: boolean | null = null, 
    filterPartner: boolean | null = null
  ) => {
    const params = new URLSearchParams({
      sort_by: sortBy,
      sort_order: sortOrder,
      limit: limit.toString(),
      offset: offset.toString()
    });
    if (search) params.append('search', search);
    if (filterBanned !== null) params.append('filter_banned', filterBanned.toString());
    if (filterPartner !== null) params.append('filter_partner', filterPartner.toString());
    return adminRequest(`/users/crm?${params.toString()}`);
  }, [adminRequest]);

  const banUserCRM = useCallback((userId: string, ban = true) => 
    adminRequest(`/users/${userId}/ban?ban=${ban}`, { method: 'POST' }), [adminRequest]);
  const updateUserBalance = useCallback((userId: string, amount: number) => 
    adminRequest(`/users/${userId}/balance?amount=${amount}`, { method: 'POST' }), [adminRequest]);
  const updateUserWarnings = useCallback((userId: string, count: number) => 
    adminRequest(`/users/${userId}/warnings?count=${count}`, { method: 'POST' }), [adminRequest]);
  
  const getPartners = useCallback(() => adminRequest('/partners'), [adminRequest]);
  const setPartner = useCallback((data: unknown) => adminRequest('/partners/set', {
    method: 'POST',
    body: JSON.stringify(data)
  }), [adminRequest]);

  const getPartnerApplications = useCallback((status = 'pending') => 
    adminRequest(`/partner-applications?status=${status}`), [adminRequest]);
  const reviewPartnerApplication = useCallback((data: unknown) => 
    adminRequest('/partner-applications/review', {
      method: 'POST',
      body: JSON.stringify(data)
    }), [adminRequest]);

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
    // Users CRM
    getUsersCRM,
    banUserCRM,
    updateUserBalance,
    updateUserWarnings,
    // Referral
    getReferralSettings,
    updateReferralSettings,
    getReferralDashboard,
    getReferralPartnersCRM,
    getPartners,
    setPartner,
    // Partner Applications
    getPartnerApplications,
    reviewPartnerApplication
  };
}

export default useAdmin;
