/**
 * Orders Adapter
 * 
 * Transforms API orders data into component-friendly format.
 */

import type { APIOrder, APIOrderItem, APIOrdersResponse } from '../types/api';
import type { Order, OrderItem, OrderStatus, OrderItemStatus } from '../types/component';

/**
 * Map API order status to component status
 */
function mapOrderStatus(apiStatus: string): OrderStatus {
  switch (apiStatus) {
    case 'delivered':
    case 'completed':
    case 'ready':
    case 'paid':
      return 'paid';
    case 'pending':
    case 'prepaid':
    case 'fulfilling':
    case 'payment_pending':
    case 'awaiting_payment':
      return 'processing';
    case 'cancelled':
    case 'refunded':
    case 'failed':
      return 'refunded';
    default:
      return 'processing';
  }
}

/**
 * Map API order item status to component status
 */
function mapOrderItemStatus(apiStatus: string): OrderItemStatus {
  switch (apiStatus) {
    case 'delivered':
    case 'completed':
    case 'ready':
      return 'delivered';
    case 'pending':
    case 'prepaid':
    case 'fulfilling':
      return 'waiting';
    case 'cancelled':
    case 'refunded':
    case 'failed':
      return 'cancelled';
    default:
      return 'waiting';
  }
}

/**
 * Format date to component display format
 */
function formatOrderDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).replace(',', ' //');
}

/**
 * Adapt a single API order item
 */
function adaptOrderItem(item: APIOrderItem): OrderItem {
  // Get credentials from delivery_content (backend) or credentials (alias)
  const credentials = item.delivery_content || item.credentials || null;
  
  return {
    id: item.id,
    name: item.product_name,
    type: item.fulfillment_type === 'instant' ? 'instant' : 'preorder',
    status: mapOrderItemStatus(item.status),
    credentials: credentials,
    instructions: item.delivery_instructions || null,
    expiry: item.expires_at ? new Date(item.expires_at).toLocaleDateString('ru-RU') : null,
    hasReview: item.has_review ?? false,
    estimatedDelivery: item.fulfillment_type === 'preorder' ? '24H' : null,
    progress: item.fulfillment_type === 'preorder' && item.status === 'fulfilling' 
      ? Math.floor(Math.random() * 80) + 20 
      : null,
    deadline: null,
    reason: null,
  };
}

/**
 * Adapt a single API order
 */
export function adaptOrder(apiOrder: APIOrder): Order {
  // Handle orders with items array (multi-item orders)
  if (apiOrder.items && apiOrder.items.length > 0) {
    return {
      id: apiOrder.id.substring(0, 8).toUpperCase(),
      date: formatOrderDate(apiOrder.created_at),
      total: apiOrder.amount_display || apiOrder.amount,
      status: mapOrderStatus(apiOrder.status),
      items: apiOrder.items.map(adaptOrderItem),
    };
  }
  
  // Handle legacy single-item orders
  return {
    id: apiOrder.id.substring(0, 8).toUpperCase(),
    date: formatOrderDate(apiOrder.created_at),
    total: apiOrder.amount_display || apiOrder.amount,
    status: mapOrderStatus(apiOrder.status),
    items: [{
      id: apiOrder.id,
      name: apiOrder.product_name,
      type: 'instant',
      status: mapOrderItemStatus(apiOrder.status),
      credentials: null,
      expiry: apiOrder.expires_at ? new Date(apiOrder.expires_at).toLocaleDateString('ru-RU') : null,
      hasReview: false,
      estimatedDelivery: null,
      progress: null,
      deadline: null,
      reason: null,
    }],
  };
}

/**
 * Adapt list of API orders
 */
export function adaptOrders(response: APIOrdersResponse): Order[] {
  return response.orders.map(adaptOrder);
}
