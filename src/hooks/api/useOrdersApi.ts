/**
 * Orders API Hook
 * 
 * Type-safe hook for fetching and creating orders.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';
import type { APIOrdersResponse, APICreateOrderRequest, APICreateOrderResponse } from '../../types/api';
import type { Order } from '../../types/component';
import { adaptOrders } from '../../adapters';

export function useOrdersTyped() {
  const { get, post, loading, error } = useApi();
  const [orders, setOrders] = useState<Order[]>([]);

  const getOrders = useCallback(async (params?: { limit?: number; offset?: number }): Promise<Order[]> => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.append('limit', params.limit.toString());
    if (params?.offset) searchParams.append('offset', params.offset.toString());
    const qs = searchParams.toString();
    
    try {
      const response: APIOrdersResponse = await get(`/orders${qs ? `?${qs}` : ''}`);
      const adapted = adaptOrders(response);
      setOrders(adapted);
      return adapted;
    } catch (err) {
      console.error('Failed to fetch orders:', err);
      return [];
    }
  }, [get]);

  const createOrder = useCallback(async (request: APICreateOrderRequest): Promise<APICreateOrderResponse | null> => {
    try {
      return await post('/orders', request);
    } catch (err) {
      console.error('Failed to create order:', err);
      return null;
    }
  }, [post]);

  return { orders, getOrders, createOrder, loading, error };
}
