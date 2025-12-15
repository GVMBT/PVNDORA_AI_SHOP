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

export const PRODUCT_CATEGORIES = ['All', 'Text', 'Image', 'Video', 'Code', 'Audio'] as const;

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

