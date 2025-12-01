import React, { useState, useEffect } from 'react'
import { useProducts, useOrders, usePromo, useCart } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Minus, Plus, Tag, Check, X, CreditCard, ShoppingBag } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent } from '../components/ui/card'
import { Separator } from '../components/ui/separator'
import { Skeleton } from '../components/ui/skeleton'

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
      if (data && data.items && Array.isArray(data.items) && data.items.length > 0) {
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
      if (!cart || !cart.items || !Array.isArray(cart.items) || cart.items.length === 0) return 0
      
      let total = cart.total || cart.subtotal || 0
      
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
      
      if (result.payment_url) {
        if (window.Telegram?.WebApp?.openLink) {
          window.Telegram.WebApp.openLink(result.payment_url)
        } else {
          window.open(result.payment_url, '_blank')
        }
        setTimeout(() => {
          if (window.Telegram?.WebApp?.close) {
            window.Telegram.WebApp.close()
          }
        }, 500)
      } else {
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
      <div className="p-4 space-y-4">
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
      </div>
    )
  }
  
  if (error || (!product && !cart)) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] p-6 text-center space-y-4">
        <div className="p-4 rounded-full bg-destructive/10 text-destructive">
          <ShoppingBag className="h-8 w-8" />
        </div>
        <p className="text-muted-foreground">
          {error || (isCartMode ? (t('checkout.cartEmpty') || 'Cart is empty') : t('product.notFound'))}
        </p>
        <Button onClick={onBack} variant="outline">
          {t('common.back')}
        </Button>
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
    <div className="pb-24">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <span className="font-semibold">{t('checkout.title')}</span>
      </div>
      
      <div className="p-4 space-y-6">
        {/* Product/Cart Summary */}
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4 space-y-4">
            {isCartMode ? (
              <>
                <h3 className="font-medium flex items-center gap-2">
                  <ShoppingBag className="h-4 w-4 text-primary" />
                  {t('checkout.cartItems') || 'Items in cart'}
                </h3>
                <div className="space-y-4">
                  {cart.items.map((item, index) => (
                    <div key={index} className="flex justify-between items-start">
                      <div className="space-y-1">
                        <p className="font-medium">{item.product_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {t('checkout.quantity')}: {item.quantity}
                          {item.instant_quantity > 0 && item.prepaid_quantity > 0 && (
                            <span className="ml-1 text-xs opacity-75">
                              ({item.instant_quantity} inst., {item.prepaid_quantity} prep.)
                            </span>
                          )}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatPrice(item.total_price)}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatPrice(item.final_price)} × {item.quantity}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <>
                <h3 className="font-semibold text-lg">{product.name}</h3>
                <Separator />
                
                {/* Quantity Control */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">{t('checkout.quantity')}</span>
                  <div className="flex items-center gap-3 bg-secondary/50 rounded-lg p-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-md hover:bg-background"
                      onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <span className="font-mono font-medium w-8 text-center">{quantity}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-md hover:bg-background"
                      onClick={() => setQuantity(quantity + 1)}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                
                {/* Unit Price */}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t('checkout.unitPrice')}</span>
                  <span>{formatPrice(product.final_price || product.price)}</span>
                </div>
              </>
            )}
          </CardContent>
        </Card>
        
        {/* Promo Code */}
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4 space-y-3">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Tag className="h-4 w-4 text-primary" />
              {t('checkout.promoCode')}
            </h3>
            <div className="flex gap-2">
              <Input
                value={promoCode}
                onChange={(e) => {
                  setPromoCode(e.target.value.toUpperCase())
                  setPromoResult(null)
                }}
                placeholder={t('checkout.promoPlaceholder')}
                className="uppercase font-mono placeholder:normal-case"
              />
              <Button
                variant="secondary"
                onClick={handlePromoCheck}
                disabled={!promoCode.trim() || promoLoading}
              >
                {promoLoading ? '...' : t('checkout.apply')}
              </Button>
            </div>
            
            {(promoResult || (isCartMode && cart.promo_code)) && (
              <div className={`flex items-center gap-2 text-sm ${
                (promoResult?.is_valid || cart.promo_discount_percent > 0) ? 'text-green-500' : 'text-destructive'
              }`}>
                {promoResult?.is_valid || cart.promo_discount_percent > 0 ? (
                  <>
                    <Check className="h-4 w-4" />
                    <span>{t('checkout.promoApplied')} -{promoResult?.discount_percent || cart.promo_discount_percent || 0}%</span>
                  </>
                ) : (
                  <>
                    <X className="h-4 w-4" />
                    <span>{promoResult?.error || t('checkout.promoInvalid')}</span>
                  </>
                )}
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Summary */}
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4 space-y-3">
            <h3 className="font-semibold">{t('checkout.summary')}</h3>
            
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t('checkout.subtotal')}</span>
                <span>{formatPrice(subtotal)}</span>
              </div>
              
              {discount > 0 && (
                <div className="flex justify-between text-green-500">
                  <span>{t('checkout.discount')}</span>
                  <span>-{formatPrice(discount)}</span>
                </div>
              )}
              
              <Separator className="my-2" />
              
              <div className="flex justify-between text-lg font-bold">
                <span>{t('checkout.total')}</span>
                <span className="text-primary">{formatPrice(total)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
        
        {/* Payment Info */}
        <div className="rounded-xl bg-secondary/30 p-4 flex items-start gap-3 text-sm text-muted-foreground">
          <CreditCard className="h-5 w-5 shrink-0 mt-0.5" />
          <p>{t('checkout.paymentInfo')}</p>
        </div>
      </div>
    </div>
  )
}
