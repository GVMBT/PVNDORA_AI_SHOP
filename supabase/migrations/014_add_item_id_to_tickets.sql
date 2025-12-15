-- Migration: Add item_id to tickets table
-- Allows tracking which specific order item (account) has an issue
-- Date: 2025-12-15

-- Add item_id column to tickets table
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS item_id UUID REFERENCES order_items(id) ON DELETE SET NULL;

-- Add comment
COMMENT ON COLUMN tickets.item_id IS 'Specific order item (account) that has an issue. NULL means issue affects entire order.';

-- Add index for faster lookups by item
CREATE INDEX IF NOT EXISTS idx_tickets_item_id ON tickets(item_id) WHERE item_id IS NOT NULL;

-- Add index for combined lookups (order + item)
CREATE INDEX IF NOT EXISTS idx_tickets_order_item ON tickets(order_id, item_id) WHERE order_id IS NOT NULL;

