import React from 'react'
import { useLocale } from '../hooks/useLocale'
import StarRating from './StarRating'

export default function ProductCard({ product, socialProof, onClick }) {
  const { formatPrice, t } = useLocale()
  
  const {
    id,
    name,
    price,
    msrp,
    discount_percent,
    final_price,
    available_count,
    can_fulfill_on_demand,
    type
  } = product
  
  const hasDiscount = discount_percent > 0
  const isInStock = available_count > 0
  const savings = msrp && final_price ? msrp - final_price : 0
  
  return (
    <button
      onClick={() => onClick(id)}
      className="card w-full text-left hover:border-[var(--color-primary)] transition-all group"
    >
      {/* Header with type badge and discount */}
      <div className="flex items-start justify-between mb-3">
        <span className="badge bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]">
          {type}
        </span>
        
        {hasDiscount && (
          <span className="badge badge-success">
            -{discount_percent}%
          </span>
        )}
      </div>
      
      {/* Product name */}
      <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2 group-hover:text-[var(--color-primary)] transition-colors">
        {name}
      </h3>
      
      {/* Social proof */}
      {socialProof && (socialProof.review_count > 0 || socialProof.sales_count > 0) && (
        <div className="flex items-center gap-3 mb-3 text-sm">
          {socialProof.rating > 0 && (
            <div className="flex items-center gap-1">
              <StarRating rating={socialProof.rating} size="sm" />
              <span className="text-[var(--color-text-muted)]">
                ({socialProof.review_count})
              </span>
            </div>
          )}
          
          {socialProof.sales_count > 0 && (
            <span className="text-[var(--color-text-muted)]">
              {socialProof.sales_count} {t('product.sold')}
            </span>
          )}
        </div>
      )}
      
      {/* Price section */}
      <div className="flex items-end justify-between mt-auto">
        <div>
          {hasDiscount && msrp && (
            <span className="price-original">{formatPrice(msrp)}</span>
          )}
          <div className="price-final">
            {formatPrice(final_price || price)}
          </div>
          {savings > 0 && (
            <span className="price-savings">
              {t('product.save')} {formatPrice(savings)}
            </span>
          )}
        </div>
        
        {/* Stock indicator */}
        <div className="text-right">
          {isInStock ? (
            <span className="badge badge-success">
              {t('product.inStock')}
            </span>
          ) : can_fulfill_on_demand ? (
            <span className="badge badge-warning">
              {t('product.onDemand')}
            </span>
          ) : (
            <span className="badge badge-error">
              {t('product.outOfStock')}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

