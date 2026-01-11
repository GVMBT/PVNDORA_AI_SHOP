-- Migration: Add 'refunded' status to order_items.status constraint
-- Date: 2026-01-11
--
-- Problem: refund_expired_prepaid cron job tries to set order_items.status = 'refunded',
-- but constraint order_items_status_check doesn't allow 'refunded'
--
-- Solution: Add 'refunded' to allowed status values for order_items

-- Step 1: Drop old constraint
ALTER TABLE order_items DROP CONSTRAINT IF EXISTS order_items_status_check;

-- Step 2: Add new constraint with 'refunded' status
ALTER TABLE order_items 
ADD CONSTRAINT order_items_status_check 
CHECK (status IN ('pending', 'prepaid', 'delivered', 'cancelled', 'refunded'));

-- Comment on the statuses
COMMENT ON COLUMN order_items.status IS 'Item status:
  - pending: Created, awaiting payment
  - prepaid: Payment confirmed, no stock, waiting for supply
  - delivered: Item delivered to user
  - cancelled: Cancelled before payment
  - refunded: Cancelled after payment, funds returned';
