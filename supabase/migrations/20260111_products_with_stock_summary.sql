-- ============================================================
-- VIEW: products_with_stock_summary
-- Eliminates N+1 queries for product listing with stock counts
-- ============================================================

CREATE OR REPLACE VIEW products_with_stock_summary AS
SELECT 
    p.id,
    p.name,
    p.description,
    p.price,
    p.prices,
    p.type,
    p.status,
    p.warranty_hours,
    p.instructions,
    p.terms,
    p.supplier_id,
    p.fulfillment_time_hours,
    p.requires_prepayment,
    p.prepayment_percent,
    p.categories,
    p.msrp,
    p.duration_days,
    p.instruction_files,
    p.image_url,
    p.video_url,
    p.logo_svg_url,
    p.discount_price,
    p.created_at,
    p.updated_at,
    -- Aggregated stock counts (no N+1!)
    COUNT(si.id) FILTER (
        WHERE si.status = 'available' 
        AND (si.expires_at IS NULL OR si.expires_at > NOW())
    ) AS stock_count,
    COUNT(si.id) FILTER (WHERE si.status = 'sold') AS sold_count,
    COUNT(si.id) FILTER (WHERE si.status = 'reserved') AS reserved_count,
    -- Max discount percent from available stock items (for catalog display)
    COALESCE(MAX(si.discount_percent) FILTER (
        WHERE si.status = 'available' 
        AND (si.expires_at IS NULL OR si.expires_at > NOW())
    ), 0) AS max_discount_percent
FROM products p
LEFT JOIN stock_items si ON p.id = si.product_id
GROUP BY p.id;

-- Grant access to authenticated users
GRANT SELECT ON products_with_stock_summary TO authenticated;
GRANT SELECT ON products_with_stock_summary TO service_role;
