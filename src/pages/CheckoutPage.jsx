import React, { useState, useEffect } from 'react'
import { useProducts, useOrders, usePromo, useCart } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

export default function CheckoutPage({ productId, initialQuantity = 1, onBack, onSuccess }) {
  const { getProduct, loading: productLoading } = useProducts()
  const { createOrder, createOrderFromCart, loading: orderLoading } = useOrders()
  const { checkPromo, loading: promoLoading } = usePromo()
  const { getCart, loading: cartLoading } = useCart()
  const { t, formatPrice } = useLocale()
  const { setBackButton, setMainButton, hapticFeedback, showAlert } = useTelegram()
  
  const [product, setProduct] = useState(null)
  const [cart, setCart] = useState(null)
  const [promoCode, setPromoCode] = useState('')
  const [promoResult, setPromoResult] = useState(null)
  const [quantity, setQuantity] = useState(initialQuantity)
  const [error, setError] = useState(null)
  const isCartMode = !productId
  
  useEffect(() => {
    if (productId) {
      loadProduct()
    } else {
      loadCart()
    }
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
      setMainButton({ isVisible: false })
    }
  }, [productId])
  
  // Update main button when product/cart/promo changes
  useEffect(() => {
    const total = calculateTotal()
    if (total > 0) {
      setMainButton({
        text: `${t('checkout.pay')} ${formatPrice(total)}`,
        isVisible: true,
        onClick: handleCheckout
      })
    }
  }, [product, cart, quantity, promoResult])
  
  const loadProduct = async () => {
    try {
      const data = await getProduct(productId)
      setProduct(data.product)
    } catch (err) {
      setError(err.message)
    }
  }
  
  const loadCart = async () => {
    try {
      const data = await getCart()
      if (data.cart && data.items && data.items.length > 0) {
        setCart(data)
        if (data.promo_code) {
          setPromoCode(data.promo_code)
        }
      } else {
        setError(t('checkout.cartEmpty') || 'Cart is empty')
      }
    } catch (err) {
      setError(err.message)
    }
  }
  
  const calculateTotal = () => {
    if (isCartMode) {
      if (!cart || !cart.items || cart.items.length === 0) return 0
      
      let total = cart.total || cart.subtotal || 0
      
      // Apply additional promo if checked
      if (promoResult?.is_valid && promoResult.discount_percent) {
        total = total * (1 - promoResult.discount_percent / 100)
      }
      
      return total
    } else {
      if (!product) return 0
      
      const price = product.final_price || product.price
      let total = price * quantity
      
      if (promoResult?.is_valid) {
        if (promoResult.discount_percent) {
          total = total * (1 - promoResult.discount_percent / 100)
        } else if (promoResult.discount_amount) {
          total = Math.max(0, total - promoResult.discount_amount)
        }
      }
      
      return total
    }
  }
  
  const handlePromoCheck = async () => {
    if (!promoCode.trim()) return
    
    try {
      const result = await checkPromo(promoCode)
      setPromoResult(result)
      
      if (result.is_valid) {
        hapticFeedback('notification', 'success')
      } else {
        hapticFeedback('notification', 'error')
      }
    } catch (err) {
      setPromoResult({ is_valid: false, error: err.message })
      hapticFeedback('notification', 'error')
    }
  }
  
  const handleCheckout = async () => {
    try {
      hapticFeedback('impact', 'medium')
      setMainButton({ isLoading: true })
      
      let result
      if (isCartMode) {
        result = await createOrderFromCart(
          promoResult?.is_valid ? promoCode : null
        )
      } else {
        result = await createOrder(
          productId, 
          quantity, 
          promoResult?.is_valid ? promoCode : null
        )
      }
      
      hapticFeedback('notification', 'success')
      
      // Redirect to payment URL (CardLink/AAIO/Stripe)
      if (result.payment_url) {
        // Open payment URL in Telegram WebApp
        if (window.Telegram?.WebApp?.openLink) {
          window.Telegram.WebApp.openLink(result.payment_url)
        } else {
          // Fallback: open in new window
          window.open(result.payment_url, '_blank')
        }
        // Close Mini App after opening payment
        setTimeout(() => {
          if (window.Telegram?.WebApp?.close) {
            window.Telegram.WebApp.close()
          }
        }, 500)
      } else {
        // No payment URL - show success message
        await showAlert(t('checkout.orderCreated'))
        onSuccess()
      }
      
    } catch (err) {
      hapticFeedback('notification', 'error')
      await showAlert(err.message)
    } finally {
      setMainButton({ isLoading: false })
    }
  }
  
  if (productLoading || cartLoading) {
    return (
      <div className="p-4">
        <div className="card h-48 skeleton mb-4" />
        <div className="card h-32 skeleton" />
      </div>
    )
  }
  
  if (error || (!product && !cart)) {
    return (
      <div className="p-4">
        <div className="card text-center py-8">
          <p className="text-[var(--color-error)] mb-4">
            {error || (isCartMode ? (t('checkout.cartEmpty') || 'Cart is empty') : t('product.notFound'))}
          </p>
          <button onClick={onBack} className="btn btn-secondary">
            {t('common.back')}
          </button>
        </div>
      </div>
    )
  }
  
  const total = calculateTotal()
  let subtotal, discount
  
  if (isCartMode) {
    subtotal = cart.subtotal || 0
    discount = subtotal - total
  } else {
    const basePrice = product.final_price || product.price
    subtotal = basePrice * quantity
    discount = subtotal - total
  }
  
  return (
    <div className="p-4 pb-20">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-[var(--color-text-muted)] mb-4 hover:text-[var(--color-text)]"
      >
        <span>←</span>
        <span>{t('common.back')}</span>
      </button>
      
      {/* Header */}
      <h1 className="text-2xl font-bold text-[var(--color-text)] mb-6 stagger-enter">
        {t('checkout.title')}
      </h1>
      
      {/* Product/Cart summary */}
      <div className="card mb-4 stagger-enter">
        {isCartMode ? (
          <>
            <h2 className="font-semibold text-[var(--color-text)] mb-3">
              {t('checkout.cartItems') || 'Items in cart'}
            </h2>
            {cart.items.map((item, index) => (
              <div key={index} className={`${index > 0 ? 'mt-4 pt-4 border-t border-[var(--color-border)]' : ''}`}>
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1">
                    <h3 className="font-medium text-[var(--color-text)]">
                      {item.product_name}
                    </h3>
                    <p className="text-sm text-[var(--color-text-muted)]">
                      {t('checkout.quantity')}: {item.quantity}
                      {item.instant_quantity > 0 && item.prepaid_quantity > 0 && (
                        <span className="ml-2">
                          ({item.instant_quantity} {t('checkout.instant') || 'instant'}, {item.prepaid_quantity} {t('checkout.prepaid') || 'prepaid'})
                        </span>
                      )}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-[var(--color-text)]">
                      {formatPrice(item.total_price)}
                    </p>
                    <p className="text-xs text-[var(--color-text-muted)]">
                      {formatPrice(item.final_price)} × {item.quantity}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </>
        ) : (
          <>
            <h2 className="font-semibold text-[var(--color-text)] mb-3">
              {product.name}
            </h2>
            
            {/* Quantity selector */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-[var(--color-text-muted)]">
                {t('checkout.quantity')}
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="w-8 h-8 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text)] flex items-center justify-center"
                >
                  -
                </button>
                <span className="font-semibold text-[var(--color-text)] w-8 text-center">
                  {quantity}
                </span>
                <button
                  onClick={() => setQuantity(quantity + 1)}
                  className="w-8 h-8 rounded-full bg-[var(--color-bg-elevated)] text-[var(--color-text)] flex items-center justify-center"
                >
                  +
                </button>
              </div>
            </div>
            
            {/* Unit price */}
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--color-text-muted)]">
                {t('checkout.unitPrice')}
              </span>
              <span className="text-[var(--color-text)]">
                {formatPrice(product.final_price || product.price)}
              </span>
            </div>
          </>
        )}
      </div>
      
      {/* Promo code */}
      <div className="card mb-4 stagger-enter">
        <h3 className="font-semibold text-[var(--color-text)] mb-3">
          🏷 {t('checkout.promoCode')}
        </h3>
        
        <div className="flex gap-2">
          <input
            type="text"
            value={promoCode}
            onChange={(e) => {
              setPromoCode(e.target.value.toUpperCase())
              setPromoResult(null)
            }}
            placeholder={t('checkout.promoPlaceholder')}
            className="flex-1 bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg px-4 py-2 text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-primary)] outline-none"
          />
          <button
            onClick={handlePromoCheck}
            disabled={!promoCode.trim() || promoLoading}
            className="btn btn-secondary px-4"
          >
            {promoLoading ? '...' : t('checkout.apply')}
          </button>
        </div>
        
        {(promoResult || (isCartMode && cart.promo_code)) && (
          <div className={`mt-2 text-sm ${(promoResult?.is_valid || cart.promo_discount_percent > 0) ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'}`}>
            {promoResult?.is_valid || cart.promo_discount_percent > 0
              ? `✓ ${t('checkout.promoApplied')} -${promoResult?.discount_percent || cart.promo_discount_percent || 0}%`
              : `✗ ${promoResult?.error || t('checkout.promoInvalid')}`
            }
          </div>
        )}
      </div>
      
      {/* Order summary */}
      <div className="card mb-4 stagger-enter">
        <h3 className="font-semibold text-[var(--color-text)] mb-4">
          {t('checkout.summary')}
        </h3>
        
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-[var(--color-text-muted)]">
              {t('checkout.subtotal')}
            </span>
            <span className="text-[var(--color-text)]">
              {formatPrice(subtotal)}
            </span>
          </div>
          
          {discount > 0 && (
            <div className="flex justify-between text-sm">
              <span className="text-[var(--color-success)]">
                {t('checkout.discount')}
              </span>
              <span className="text-[var(--color-success)]">
                -{formatPrice(discount)}
              </span>
            </div>
          )}
          
          <div className="pt-3 border-t border-[var(--color-border)] flex justify-between">
            <span className="font-semibold text-[var(--color-text)]">
              {t('checkout.total')}
            </span>
            <span className="font-bold text-xl text-[var(--color-primary)]">
              {formatPrice(total)}
            </span>
          </div>
        </div>
      </div>
      
      {/* Payment methods info */}
      <div className="card bg-[var(--color-bg-elevated)] stagger-enter">
        <h3 className="font-semibold text-[var(--color-text)] mb-2">
          💳 {t('checkout.paymentMethods')}
        </h3>
        <p className="text-[var(--color-text-muted)] text-sm">
          {t('checkout.paymentInfo')}
        </p>
      </div>
      
      {/* Checkout button is handled by Telegram MainButton via setMainButton */}
      {/* No need for duplicate HTML button */}
    </div>
  )
}


