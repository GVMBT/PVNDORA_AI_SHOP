-- Add original_price before discount
ALTER TABLE public.orders 
ADD COLUMN IF NOT EXISTS original_price NUMERIC;

-- Add discount_percent applied
ALTER TABLE public.orders 
ADD COLUMN IF NOT EXISTS discount_percent NUMERIC DEFAULT 0;

-- Add refund_requested flag
ALTER TABLE public.orders 
ADD COLUMN IF NOT EXISTS refund_requested BOOLEAN DEFAULT false;

-- Add payment_id for external reference
ALTER TABLE public.orders 
ADD COLUMN IF NOT EXISTS payment_id TEXT;

COMMENT ON COLUMN public.orders.original_price IS 'Price before discount';
COMMENT ON COLUMN public.orders.discount_percent IS 'Discount percentage applied';
COMMENT ON COLUMN public.orders.refund_requested IS 'User requested refund';
COMMENT ON COLUMN public.orders.payment_id IS 'External payment system ID';

