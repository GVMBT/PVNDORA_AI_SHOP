/**
 * Application Constants
 * 
 * Centralized constants for order statuses, payment methods, product categories, etc.
 */

/**
 * Order Status Constants
 */
export const ORDER_STATUSES = {
  PENDING: 'pending',
  PREPAID: 'prepaid',
  PAID: 'paid',
  PROCESSING: 'processing',
  PARTIAL: 'partial',
  DELIVERED: 'delivered',
  COMPLETED: 'completed',
  READY: 'ready',
  CANCELLED: 'cancelled',
  REFUNDED: 'refunded',
  EXPIRED: 'expired',
  FAILED: 'failed',
  AWAITING_PAYMENT: 'awaiting_payment',
} as const;

export type OrderStatus = typeof ORDER_STATUSES[keyof typeof ORDER_STATUSES];

/**
 * Payment Gateway Constants
 */
export const PAYMENT_GATEWAYS = {
  ONEPLAT: 'oneplat',
  RUKASSA: 'rukassa',
  CRYPTO: 'crypto',
} as const;

export type PaymentGateway = typeof PAYMENT_GATEWAYS[keyof typeof PAYMENT_GATEWAYS];

/**
 * Payment Method Constants
 */
export const PAYMENT_METHODS = {
  CARD: 'card',
  SBP: 'sbp',
  CRYPTO: 'crypto',
  BANK: 'bank',
} as const;

export type PaymentMethod = typeof PAYMENT_METHODS[keyof typeof PAYMENT_METHODS];

/**
 * Payment Method Groups
 */
export const PAYMENT_METHOD_GROUPS = {
  CARD: 'card',
  SBP: 'sbp',
  CRYPTO: 'crypto',
  BANK: 'bank',
} as const;

export type PaymentMethodGroup = typeof PAYMENT_METHOD_GROUPS[keyof typeof PAYMENT_METHOD_GROUPS];

/**
 * Product Category Constants
 */
export const PRODUCT_CATEGORIES = {
  TEXT: 'Text',
  ACCOUNT: 'Account',
  KEY: 'Key',
  CODE: 'Code',
  SUBSCRIPTION: 'Subscription',
  SERVICE: 'Service',
} as const;

export type ProductCategory = typeof PRODUCT_CATEGORIES[keyof typeof PRODUCT_CATEGORIES];

/**
 * Product Type Constants
 */
export const PRODUCT_TYPES = {
  INSTANT: 'instant',
  PREORDER: 'preorder',
} as const;

export type ProductType = typeof PRODUCT_TYPES[keyof typeof PRODUCT_TYPES];

/**
 * User Role Constants
 */
export const USER_ROLES = {
  USER: 'USER',
  VIP: 'VIP',
  ADMIN: 'ADMIN',
} as const;

export type UserRole = typeof USER_ROLES[keyof typeof USER_ROLES];

/**
 * Support Ticket Status Constants
 */
export const TICKET_STATUSES = {
  OPEN: 'open',
  APPROVED: 'approved',
  REJECTED: 'rejected',
  CLOSED: 'closed',
} as const;

export type TicketStatus = typeof TICKET_STATUSES[keyof typeof TICKET_STATUSES];

/**
 * Currency Constants
 */
export const CURRENCIES = {
  USD: 'USD',
  RUB: 'RUB',
  EUR: 'EUR',
} as const;

export type Currency = typeof CURRENCIES[keyof typeof CURRENCIES];

/**
 * Language Constants
 */
export const LANGUAGES = {
  EN: 'en',
  RU: 'ru',
  DE: 'de',
  ES: 'es',
  FR: 'fr',
  IT: 'it',
  PT: 'pt',
  TR: 'tr',
  UK: 'uk',
} as const;

export type Language = typeof LANGUAGES[keyof typeof LANGUAGES];

/**
 * Helper function to check if a string is a valid order status
 */
export function isValidOrderStatus(status: string): status is OrderStatus {
  return Object.values(ORDER_STATUSES).includes(status as OrderStatus);
}

/**
 * Helper function to check if a string is a valid payment method
 */
export function isValidPaymentMethod(method: string): method is PaymentMethod {
  return Object.values(PAYMENT_METHODS).includes(method as PaymentMethod);
}

/**
 * Helper function to check if a string is a valid user role
 */
export function isValidUserRole(role: string): role is UserRole {
  return Object.values(USER_ROLES).includes(role as UserRole);
}


