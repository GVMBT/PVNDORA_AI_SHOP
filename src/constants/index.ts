/**
 * PVNDORA Business Constants
 * 
 * Centralized repository for all business logic constants, enums, and static data.
 * Does NOT include environment configuration (see src/config.ts).
 */

import type { CareerLevelData } from '../components/profile/types';

// ==========================================
// PRODUCT CATALOG
// ==========================================

// Categories matching database product.type values
export const PRODUCT_CATEGORIES = ['All', 'ai', 'dev', 'design', 'music'] as const;

// Display labels for categories
export const PRODUCT_CATEGORY_LABELS: Record<string, string> = {
  'All': 'All',
  'ai': 'AI & Text',
  'dev': 'Development',
  'design': 'Design & Image',
  'music': 'Audio & Music'
};

export const PRODUCT_AVAILABILITY = {
  FILTERS: ['All', 'Available', 'On Demand', 'Discontinued'] as const,
  STATUS: {
    AVAILABLE: 'available',
    ON_DEMAND: 'on_demand',
    DISCONTINUED: 'discontinued',
    COMING_SOON: 'coming_soon',
  } as const
} as const;

export type AvailabilityFilter = typeof PRODUCT_AVAILABILITY.FILTERS[number];
export type ProductAvailability = typeof PRODUCT_AVAILABILITY.STATUS[keyof typeof PRODUCT_AVAILABILITY.STATUS];

// ==========================================
// ORDERS & PAYMENTS
// ==========================================

export const PAYMENT_STATUS = {
  CHECKING: 'checking',
  PAID: 'paid',
  PREPAID: 'prepaid',
  DELIVERED: 'delivered',
  PARTIAL: 'partial',
  PENDING: 'pending',
  CANCELLED: 'cancelled',
  REFUNDED: 'refunded',
  EXPIRED: 'expired',
  FAILED: 'failed',
  UNKNOWN: 'unknown',
} as const;

export type PaymentStatus = typeof PAYMENT_STATUS[keyof typeof PAYMENT_STATUS];

export const PAYMENT_STATUS_MESSAGES: Record<PaymentStatus, { color: string; label: string; description: string }> = {
  checking: { color: 'purple', label: 'VERIFYING', description: 'Checking payment status...' },
  paid: { color: 'green', label: 'CONFIRMED', description: 'Payment confirmed! Preparing delivery...' },
  prepaid: { color: 'cyan', label: 'PREORDER', description: 'Payment confirmed! Awaiting stock for delivery.' },
  delivered: { color: 'cyan', label: 'COMPLETE', description: 'All items delivered to your account!' },
  partial: { color: 'yellow', label: 'PARTIAL', description: 'Some items delivered, preorder items in queue.' },
  pending: { color: 'orange', label: 'PENDING', description: 'Waiting for payment confirmation...' },
  cancelled: { color: 'red', label: 'CANCELLED', description: 'Order was cancelled.' },
  refunded: { color: 'red', label: 'REFUNDED', description: 'Payment has been refunded.' },
  expired: { color: 'red', label: 'EXPIRED', description: 'Payment link has expired.' },
  failed: { color: 'red', label: 'FAILED', description: 'Payment failed. Please try again.' },
  unknown: { color: 'gray', label: 'UNKNOWN', description: 'Unable to determine status.' },
};

// ==========================================
// USER PROFILE & CAREER
// ==========================================

// CAREER_LEVELS removed - thresholds now loaded from DB via API
// See profileAdapter.ts which uses thresholds_usd from referral_settings table

// ==========================================
// SYSTEM
// ==========================================

export const STORAGE_KEYS = {
  BOOT_STATE: 'pvndora_booted',
  SESSION_TOKEN: 'pvndora_session',
  CART: 'pvndora_cart',
} as const;

export const API_ENDPOINTS = {
  WEBAPP: '/api/webapp',
  ADMIN: '/api/admin',
} as const;

