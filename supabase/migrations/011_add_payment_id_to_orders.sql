-- Migration: Add payment_id to orders for payment gateway linkage
-- Ensures we can persist and query external payment references (id/guid)

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS payment_id TEXT;

-- Index for webhook lookups by payment_id/guid
CREATE INDEX IF NOT EXISTS idx_orders_payment_id ON orders(payment_id);
