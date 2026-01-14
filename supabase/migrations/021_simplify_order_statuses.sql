-- Migration: Simplify order statuses
-- Remove unused statuses: fulfilling, ready, failed, expired
-- Keep only: pending, paid, prepaid, delivered, cancelled, refunded

-- Step 1: Drop old constraint
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;

-- Step 2: Add new simplified constraint
ALTER TABLE orders 
ADD CONSTRAINT orders_status_check 
CHECK (status IN ('pending', 'paid', 'prepaid', 'delivered', 'cancelled', 'refunded'));

-- Step 3: Update any old statuses to valid ones (safety net)
UPDATE orders SET status = 'refunded' WHERE status IN ('failed', 'expired');
UPDATE orders SET status = 'prepaid' WHERE status IN ('fulfilling', 'ready');

-- Comment on the simplified statuses
COMMENT ON TABLE orders IS 'Order statuses: pending (Created, awaiting payment), paid (Payment confirmed, stock available, preparing delivery), prepaid (Payment confirmed, no stock, waiting for supply), delivered (Items delivered to user), cancelled (Cancelled before payment), refunded (Cancelled after payment, funds returned)';
