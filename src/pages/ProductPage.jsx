import React, { useState, useEffect } from 'react'
import { useProducts } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import StarRating from '../components/StarRating'

export default function ProductPage({ productId, onBack, onCheckout }) {
  const { getProduct, loading, error } = useProducts()
  const { t, formatPrice, formatDate } = useLocale()
  const { setBackButton, hapticFeedback } = useTelegram()
  
  const [product, setProduct] = useState(null)
  const [socialProof, setSocialProof] = useState(null)
  
  useEffect(() => {
    loadProduct()
    
    // Setup back button
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [productId])
  
  const loadProduct = async () => {
    try {
      const data = await getProduct(productId)
      setProduct(data.product)
      setSocialProof(data.social_proof)
    } catch (err) {
      console.error('Failed to load product:', err)
    }
  }
  
  const handleBuy = () => {
    hapticFeedback('impact', 'medium')
    onCheckout()
  }
  
  if (loading) {
    return (
      <div className="p-4">
        <div className="card h-64 skeleton mb-4" />
        <div className="card h-32 skeleton mb-4" />
        <div className="card h-48 skeleton" />
      </div>
    )
  }
  
  if (error || !product) {
    return (
      <div className="p-4">
        <div className="card text-center py-8">
          <p className="text-[var(--color-error)] mb-4">
            {error || t('product.notFound')}
          </p>
          <button onClick={onBack} className="btn btn-secondary">
            {t('common.back')}
          </button>
        </div>
      </div>
    )
  }
  
  const {
    name,
    description,
    price,
    msrp,
    discount_percent,
    final_price,
    available_count,
    can_fulfill_on_demand,
    fulfillment_time_hours,
    type,
    warranty_days,
    duration_days,
    instructions
  } = product
  
  const hasDiscount = discount_percent > 0
  const isInStock = available_count > 0
  const savings = msrp && final_price ? msrp - final_price : 0
  
  return (
    <div className="p-4 pb-24">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-[var(--color-text-muted)] mb-4 hover:text-[var(--color-text)]"
      >
        <span>←</span>
        <span>{t('common.back')}</span>
      </button>
      
      {/* Product header */}
      <div className="card mb-4 stagger-enter">
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
        
        <h1 className="text-2xl font-bold text-[var(--color-text)] mb-2">
          {name}
        </h1>
        
        {description && (
          <p className="text-[var(--color-text-muted)] mb-4">
            {description}
          </p>
        )}
        
        {/* Social proof */}
        {socialProof && (
          <div className="flex items-center gap-4 mb-4">
            {socialProof.rating > 0 && (
              <div className="flex items-center gap-2">
                <StarRating rating={socialProof.rating} showValue />
                <span className="text-[var(--color-text-muted)] text-sm">
                  ({socialProof.review_count} {t('product.reviews')})
                </span>
              </div>
            )}
            {socialProof.sales_count > 0 && (
              <span className="text-[var(--color-text-muted)] text-sm">
                {socialProof.sales_count}+ {t('product.sold')}
              </span>
            )}
          </div>
        )}
        
        {/* Price */}
        <div className="flex items-end gap-3 mb-4">
          <span className="price-final">
            {formatPrice(final_price || price)}
          </span>
          {hasDiscount && msrp && (
            <span className="price-original">
              {formatPrice(msrp)}
            </span>
          )}
        </div>
        
        {savings > 0 && (
          <div className="bg-[var(--color-success)]/10 rounded-lg p-3 mb-4">
            <span className="text-[var(--color-success)] font-semibold">
              💰 {t('product.save')} {formatPrice(savings)}
            </span>
          </div>
        )}
        
        {/* Stock status */}
        <div className="flex items-center gap-2 mb-4">
          {isInStock ? (
            <>
              <span className="w-2 h-2 bg-[var(--color-success)] rounded-full animate-pulse" />
              <span className="text-[var(--color-success)]">
                {t('product.inStock')} ({available_count} {t('product.available')})
              </span>
            </>
          ) : can_fulfill_on_demand ? (
            <>
              <span className="w-2 h-2 bg-[var(--color-warning)] rounded-full" />
              <span className="text-[var(--color-warning)]">
                {t('product.onDemand')} (~{fulfillment_time_hours}h)
              </span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 bg-[var(--color-error)] rounded-full" />
              <span className="text-[var(--color-error)]">
                {t('product.outOfStock')}
              </span>
            </>
          )}
        </div>
        
        {/* Details */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          {warranty_days > 0 && (
            <div className="bg-[var(--color-bg-elevated)] rounded-lg p-3">
              <span className="text-[var(--color-text-muted)]">{t('product.warranty')}</span>
              <div className="font-semibold">{warranty_days} {t('common.days')}</div>
            </div>
          )}
          {duration_days > 0 && (
            <div className="bg-[var(--color-bg-elevated)] rounded-lg p-3">
              <span className="text-[var(--color-text-muted)]">{t('product.duration')}</span>
              <div className="font-semibold">{duration_days} {t('common.days')}</div>
            </div>
          )}
        </div>
      </div>
      
      {/* Instructions */}
      {instructions && (
        <div className="card mb-4 stagger-enter">
          <h2 className="font-semibold text-[var(--color-text)] mb-2">
            {t('product.instructions')}
          </h2>
          <p className="text-[var(--color-text-muted)] text-sm whitespace-pre-wrap">
            {instructions}
          </p>
        </div>
      )}
      
      {/* Reviews */}
      {socialProof?.recent_reviews?.length > 0 && (
        <div className="card mb-4 stagger-enter">
          <h2 className="font-semibold text-[var(--color-text)] mb-4">
            {t('product.recentReviews')}
          </h2>
          <div className="space-y-4">
            {socialProof.recent_reviews.map((review, index) => (
              <div key={index} className="border-b border-[var(--color-border)] last:border-0 pb-3 last:pb-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-[var(--color-text)]">
                    {review.author}
                  </span>
                  <StarRating rating={review.rating} size="sm" />
                </div>
                {review.text && (
                  <p className="text-[var(--color-text-muted)] text-sm">
                    {review.text}
                  </p>
                )}
                <span className="text-[var(--color-text-muted)] text-xs">
                  {formatDate(review.date)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Buy button - fixed at bottom */}
      <div className="fixed bottom-20 left-0 right-0 p-4 bg-gradient-to-t from-[var(--color-bg-dark)] to-transparent">
        <button
          onClick={handleBuy}
          disabled={!isInStock && !can_fulfill_on_demand}
          className="btn btn-primary w-full glow-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isInStock ? t('product.buyNow') : can_fulfill_on_demand ? t('product.preorder') : t('product.notifyMe')}
        </button>
      </div>
    </div>
  )
}



