import React, { useState, useEffect } from 'react'
import { useProducts, useOrders, usePromo, useCart } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Minus, Plus, Tag, Check, X, CreditCard, ShoppingBag, Receipt, ShieldCheck } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Card, CardContent } from '../components/ui/card'
import { Separator } from '../components/ui/separator'
import { Skeleton } from '../components/ui/skeleton'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '../lib/utils'

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
      <div className="p-6 space-y-6">
        <Skeleton className="h-20 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-32 w-full rounded-2xl" />
      </div>
    )
  }
  
  if (error || (!product && !cart)) {
    return (
      <div className="flex flex-col items-center justify-center h-[80vh] p-6 text-center space-y-6">
        <div className="p-6 rounded-full bg-destructive/10 text-destructive">
          <ShoppingBag className="h-12 w-12" />
        </div>
        <h3 className="text-xl font-bold">
          {error || (isCartMode ? (t('checkout.cartEmpty') || 'Cart is empty') : t('product.notFound'))}
        </h3>
        <Button onClick={onBack} variant="outline" className="rounded-full px-8">
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
    <div className="min-h-screen bg-background pb-24 relative">
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-background pointer-events-none" />
      
      {/* Header */}
      <div className="sticky top-0 z-10 backdrop-blur-md border-b border-border/10 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-10 w-10 rounded-full bg-secondary/30 hover:bg-secondary/50">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <span className="font-bold text-lg">{t('checkout.title')}</span>
      </div>
      
      <div className="p-4 space-y-6 relative z-10">
        
        {/* Order Item(s) */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
            <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider pl-1">
              {t('checkout.summary')}
            </h3>
            
            <Card className="border-0 bg-card/40 backdrop-blur-xl shadow-lg ring-1 ring-white/10 overflow-hidden">
              <CardContent className="p-0">
                {isCartMode ? (
                   <div className="divide-y divide-white/5">
                     {cart.items.map((item, index) => (
                       <div key={index} className="p-4 flex justify-between items-center">
                          <div>
                             <p className="font-bold text-foreground">{item.product_name}</p>
                             <p className="text-xs text-muted-foreground mt-1">
                               {item.quantity} x {formatPrice(item.final_price)}
                             </p>
                          </div>
                          <p className="font-mono font-bold">{formatPrice(item.total_price)}</p>
                       </div>
                     ))}
                   </div>
                ) : (
                  <div className="p-5">
                    <div className="flex justify-between items-start mb-4">
                      <h2 className="text-xl font-bold leading-tight pr-4">{product.name}</h2>
                      <p className="font-mono text-primary font-bold text-lg whitespace-nowrap">
                        {formatPrice(product.final_price || product.price)}
                      </p>
                    </div>
                    
                    <div className="flex items-center justify-between bg-secondary/30 p-2 rounded-xl">
                        <span className="text-sm font-medium pl-2">{t('checkout.quantity')}</span>
                        <div className="flex items-center gap-3 bg-background rounded-lg p-1 shadow-sm">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 rounded-md hover:bg-secondary"
                          onClick={() => {
                            hapticFeedback('selection')
                            setQuantity(Math.max(1, quantity - 1))
                          }}
                        >
                          <Minus className="h-4 w-4" />
                        </Button>
                        <span className="font-mono font-bold w-6 text-center">{quantity}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 rounded-md hover:bg-secondary"
                          onClick={() => {
                            hapticFeedback('selection')
                            setQuantity(quantity + 1)
                          }}
                        >
                          <Plus className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
        </motion.div>
        
        {/* Promo Code */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <Card className="border-0 bg-card/40 backdrop-blur-xl shadow-lg ring-1 ring-white/10">
             <CardContent className="p-4">
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      value={promoCode}
                      onChange={(e) => {
                        setPromoCode(e.target.value.toUpperCase())
                        setPromoResult(null)
                      }}
                      placeholder={t('checkout.promoPlaceholder')}
                      className="pl-9 uppercase font-mono placeholder:normal-case bg-secondary/30 border-transparent focus:border-primary/50"
                    />
                  </div>
                  <Button
                    variant="secondary"
                    onClick={handlePromoCheck}
                    disabled={!promoCode.trim() || promoLoading}
                    className="bg-secondary/50 hover:bg-secondary"
                  >
                    {promoLoading ? '...' : t('checkout.apply')}
                  </Button>
                </div>
                
                 <AnimatePresence>
                  {(promoResult || (isCartMode && cart.promo_code)) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className={`flex items-center gap-2 text-sm mt-3 p-2 rounded-lg ${
                        (promoResult?.is_valid || cart.promo_discount_percent > 0) 
                          ? 'bg-green-500/10 text-green-500' 
                          : 'bg-destructive/10 text-destructive'
                      }`}>
                        {promoResult?.is_valid || cart.promo_discount_percent > 0 ? (
                          <>
                            <Check className="h-4 w-4" />
                            <span className="font-bold">{t('checkout.promoApplied')} -{promoResult?.discount_percent || cart.promo_discount_percent || 0}%</span>
                          </>
                        ) : (
                          <>
                            <X className="h-4 w-4" />
                            <span>{promoResult?.error || t('checkout.promoInvalid')}</span>
                          </>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
             </CardContent>
          </Card>
        </motion.div>
        
        {/* Total Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
           <Card className="border-0 bg-gradient-to-br from-card/50 to-background shadow-xl ring-1 ring-white/10">
             <CardContent className="p-6 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">{t('checkout.subtotal')}</span>
                  <span className="font-mono">{formatPrice(subtotal)}</span>
                </div>
                
                {discount > 0 && (
                  <div className="flex justify-between text-sm text-green-500">
                    <span>{t('checkout.discount')}</span>
                    <span className="font-mono">-{formatPrice(discount)}</span>
                  </div>
                )}
                
                <Separator className="bg-white/10 my-2" />
                
                <div className="flex justify-between items-end">
                  <span className="font-bold text-lg">{t('checkout.total')}</span>
                  <span className="text-3xl font-bold text-primary font-mono tracking-tighter">
                    {formatPrice(total)}
                  </span>
                </div>
             </CardContent>
           </Card>
        </motion.div>
        
        {/* Trust Badge */}
        <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground opacity-70">
           <ShieldCheck className="h-3 w-3" />
           <span>{t('checkout.paymentInfo')}</span>
        </div>
      </div>
    </div>
  )
}
