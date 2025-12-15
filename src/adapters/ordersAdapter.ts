/**
 * Orders Adapter
 * 
 * Transforms API orders data into component-friendly format.
 */

import type { APIOrder, APIOrderItem, APIOrdersResponse } from '../types/api';
import type { Order, OrderItem, OrderStatus, OrderItemStatus, RawOrderStatus } from '../types/component';

/**
 * Map API order status to component status (simplified for UI tabs)
 */
function mapOrderStatus(apiStatus: string): OrderStatus {
  switch (apiStatus) {
    case 'delivered':
      return 'paid'; // Completed orders
    case 'paid':
    case 'partial':
      return 'paid'; // Paid orders
    case 'prepaid':
    case 'pending':
      return 'processing';
    case 'cancelled':
    case 'refunded':
      return 'refunded';
    default:
      return 'processing';
  }
}

/**
 * Normalize raw status from API
 */
function normalizeRawStatus(apiStatus: string): RawOrderStatus {
  const normalized = apiStatus.toLowerCase();
  const validStatuses: RawOrderStatus[] = [
    'pending', 'paid', 'prepaid', 'partial', 'delivered', 'cancelled', 'refunded'
  ];
  return validStatuses.includes(normalized as RawOrderStatus) 
    ? normalized as RawOrderStatus 
    : 'pending';
}

/**
 * Check if payment is confirmed based on status
 */
function isPaymentConfirmed(rawStatus: RawOrderStatus): boolean {
  return ['prepaid', 'paid', 'partial', 'delivered'].includes(rawStatus);
}

/**
 * Generate human-readable status message
 */
function getStatusMessage(rawStatus: RawOrderStatus): string {
  switch (rawStatus) {
    case 'pending':
      return 'AWAITING_PAYMENT — Ожидается оплата';
    case 'prepaid':
      return 'PAYMENT_CONFIRMED — Оплачено ✓ Товар временно отсутствует на складе. Доставим при поступлении.';
    case 'paid':
      return 'PROCESSING — Оплачено ✓ Идёт подготовка к выдаче';
    case 'partial':
      return 'PARTIAL_DELIVERY — Часть товаров доставлена';
    case 'delivered':
      return 'COMPLETED — Все товары доставлены';
    case 'cancelled':
      return 'CANCELLED — Заказ отменён';
    case 'refunded':
      return 'REFUNDED — Средства возвращены';
    default:
      return 'UNKNOWN — Статус неизвестен';
  }
}

/**
 * Check if order can be cancelled
 */
function canCancelOrder(rawStatus: RawOrderStatus): boolean {
  return ['pending'].includes(rawStatus);
}

/**
 * Check if refund can be requested
 * Refund is only available for DELIVERED orders within WARRANTY period
 * For prepaid orders, refund is AUTOMATIC if delivery deadline is exceeded
 */
function canRequestRefund(rawStatus: RawOrderStatus, warrantyUntil?: string | null): boolean {
  // Only delivered orders can request refund (for warranty issues)
  if (rawStatus !== 'delivered') return false;
  
  // Check if still within warranty period
  if (warrantyUntil) {
    const warrantyEnd = new Date(warrantyUntil);
    return new Date() < warrantyEnd;
  }
  
  // If no warranty info, assume 7 days from delivery
  return true;
}

/**
 * Map API order item status to component status
 */
function mapOrderItemStatus(apiStatus: string): OrderItemStatus {
  switch (apiStatus) {
    case 'delivered':
      return 'delivered';
    case 'pending':
    case 'prepaid':
    case 'paid':
    case 'partial':
      return 'waiting';
    case 'cancelled':
    case 'refunded':
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
 * Format date with timezone for display
 */
function formatDateWithTimezone(dateString: string): string {
  const date = new Date(dateString);
  const tzOffset = -date.getTimezoneOffset() / 60;
  const tzSign = tzOffset >= 0 ? '+' : '';
  const tzString = `UTC${tzSign}${tzOffset}`;
  
  return date.toLocaleString('ru-RU', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).replace(',', ' //') + ` (${tzString})`;
}

/**
 * Adapt a single API order item
 * 
 * @param item - Order item from API
 * @param orderStatus - Parent order status (pending/prepaid/delivered etc)
 * @param paymentDeadline - expires_at (only relevant for pending orders)
 * @param deliveryDeadline - fulfillment_deadline (for prepaid orders)
 */
function adaptOrderItem(
  item: APIOrderItem, 
  orderStatus: string,
  paymentDeadline?: string | null,
  deliveryDeadline?: string | null
): OrderItem {
  // Get credentials from delivery_content (backend) or credentials (alias)
  const credentials = item.delivery_content || item.credentials || null;
  
  // Determine deadline based on order status
  let deadline: string | null = null;
  
  if (orderStatus === 'pending' && paymentDeadline) {
    // For pending (unpaid) orders, show payment deadline
    deadline = formatDateWithTimezone(paymentDeadline);
  } else if (['prepaid', 'paid', 'partial'].includes(orderStatus)) {
    // For prepaid/processing orders, show delivery deadline
    if (deliveryDeadline) {
      deadline = formatDateWithTimezone(deliveryDeadline);
    } else {
      // No specific deadline set - show waiting message instead
      deadline = null; // Will show "Ожидание поступления" in UI
    }
  }
  // For delivered/cancelled/refunded - no deadline needed
  
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
    progress: null, // Progress bar removed - simplified status model
    deadline: deadline,
    reason: null,
  };
}

/**
 * Adapt a single API order
 */
export function adaptOrder(apiOrder: APIOrder, currency: string = 'USD'): Order {
  const rawStatus = normalizeRawStatus(apiOrder.status);
  const paymentConfirmed = isPaymentConfirmed(rawStatus);
  const statusMessage = getStatusMessage(rawStatus);
  const canCancel = canCancelOrder(rawStatus);
  const canRefund = canRequestRefund(rawStatus, apiOrder.warranty_until);
  
  // Handle orders with items array (multi-item orders)
  if (apiOrder.items && apiOrder.items.length > 0) {
    return {
      id: apiOrder.id, // Full UUID for API operations
      displayId: apiOrder.id.substring(0, 8).toUpperCase(), // Short ID for UI
      date: formatOrderDate(apiOrder.created_at),
      total: apiOrder.amount_display || apiOrder.amount,
      currency: apiOrder.currency || currency,
      status: mapOrderStatus(apiOrder.status),
      items: apiOrder.items.map(item => adaptOrderItem(
        item, 
        apiOrder.status,
        apiOrder.expires_at,
        apiOrder.fulfillment_deadline
      )),
      payment_url: apiOrder.payment_url || null,
      rawStatus,
      paymentConfirmed,
      statusMessage,
      canCancel,
      canRequestRefund: canRefund,
    };
  }
  
  // Handle legacy single-item orders
  // Determine deadline based on status
  let deadline: string | null = null;
  
  if (rawStatus === 'pending' && apiOrder.expires_at) {
    // For pending orders, show payment deadline
    deadline = formatDateWithTimezone(apiOrder.expires_at);
  } else if (['prepaid', 'fulfilling', 'paid'].includes(rawStatus)) {
    // For prepaid/processing orders, show delivery deadline if available
    if (apiOrder.fulfillment_deadline) {
      deadline = formatDateWithTimezone(apiOrder.fulfillment_deadline);
    }
    // If no fulfillment_deadline, deadline stays null (UI will show "Ожидание")
  }
  // For delivered/cancelled/refunded - no deadline
  
  return {
    id: apiOrder.id, // Full UUID for API operations
    displayId: apiOrder.id.substring(0, 8).toUpperCase(), // Short ID for UI
    date: formatOrderDate(apiOrder.created_at),
    total: apiOrder.amount_display || apiOrder.amount,
    currency: apiOrder.currency || currency,
    status: mapOrderStatus(apiOrder.status),
    items: [{
      id: apiOrder.id,
      name: apiOrder.product_name,
      type: 'instant',
      status: mapOrderItemStatus(apiOrder.status),
      credentials: null,
      expiry: apiOrder.warranty_until ? new Date(apiOrder.warranty_until).toLocaleDateString('ru-RU') : null,
      hasReview: false,
      estimatedDelivery: null,
      progress: null,
      deadline: deadline,
      reason: null,
    }],
    payment_url: apiOrder.payment_url || null,
    rawStatus,
    paymentConfirmed,
    statusMessage,
    canCancel,
    canRequestRefund: canRefund,
  };
}

/**
 * Adapt list of API orders
 */
export function adaptOrders(response: APIOrdersResponse): Order[] {
  const currency = response.currency || 'USD';
  return response.orders.map(order => adaptOrder(order, currency));
}
