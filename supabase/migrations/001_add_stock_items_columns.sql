-- Add expires_at for subscription expiration tracking
ALTER TABLE public.stock_items 
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Add supplier_id foreign key
ALTER TABLE public.stock_items 
ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES public.suppliers(id);

-- Create index for finding expiring items
CREATE INDEX IF NOT EXISTS idx_stock_items_expires_at ON public.stock_items(expires_at);

-- Create index for supplier lookup
CREATE INDEX IF NOT EXISTS idx_stock_items_supplier_id ON public.stock_items(supplier_id);

COMMENT ON COLUMN public.stock_items.expires_at IS 'When the subscription/access expires';
COMMENT ON COLUMN public.stock_items.supplier_id IS 'Supplier who provided this item';

